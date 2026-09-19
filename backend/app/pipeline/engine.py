"""CollapseCastEngine: trains the cascade once, then turns raw signals into full API results."""
from __future__ import annotations

import threading
from typing import Any, Mapping, Sequence

import numpy as np

from app.config import (
    BAND_THRESHOLDS,
    BEHAVIOR_SIGNALS,
    RISK_MODE,
    RISK_SIGNALS,
    SIGNAL_LABELS,
    STAGE_ACTIVE_THRESHOLD,
    STAGES,
)
from app.data.batch import SignalBatch
from app.data.loader import load_dataset, load_samples
from app.ml.demand import DemandResult
from app.pipeline.cascade import Cascade, StageOutputs
from app.pipeline.explain import describe_signal, signal_impacts, stage_contributions
from app.pipeline.resources import actions_for, band_for, priority_percentile, rank_by_failure

_STAGE_NAMES = {number: (name, description) for number, name, description in STAGES}
_MIN_DRIVER_IMPACT = 0.01  # ignore drivers that move the failure score by less than one point


def _r(x: float, digits: int = 4) -> float:
    return round(float(x), digits)


class CollapseCastEngine:
    def __init__(self, risk_mode: str = RISK_MODE):
        self.cascade = Cascade(risk_mode=risk_mode)
        self.samples: list[dict] = []
        # Model prediction is millisecond-scale; serialising it sidesteps any doubt about
        # thread-safety of the underlying predict calls while FastAPI runs sync endpoints in a pool.
        self._lock = threading.Lock()

    @classmethod
    def train(cls, risk_mode: str = RISK_MODE) -> "CollapseCastEngine":
        engine = cls(risk_mode)
        dataset = load_dataset()
        engine.cascade.fit(dataset.batch, dataset.collapsed)
        # Order the demo companies from healthiest to sickest so a picker reads as a spectrum.
        samples = load_samples()
        scores = engine.analyze(samples)
        order = sorted(range(len(samples)), key=lambda i: scores[i]["scores"]["failure_raw"])
        engine.samples = [samples[i] for i in order]
        return engine

    def info(self) -> dict:
        return {
            "metrics": self.cascade.metrics,
            "bands": [{"band": b, "min_failure_score": t} for b, t in BAND_THRESHOLDS]
            + [{"band": "GREEN", "min_failure_score": 0.0}],
            "stage_active_threshold": STAGE_ACTIVE_THRESHOLD,
        }

    # --- analysis -------------------------------------------------------------------------
    def analyze(self, records: Sequence[Mapping[str, Any]], *, rank: bool = False) -> list[dict]:
        """Full result for each company. With ``rank=True`` (stage 5 sort) results come back ordered
        by Failure_raw_score, highest first, each with a 1-based ``priority_rank``."""
        batch = SignalBatch.from_records(records)
        c = self.cascade
        with self._lock:
            out = c.score(batch)
            names, impacts, baseline_scores = signal_impacts(c, batch)
            risk_contrib = stage_contributions(c.risk.predict, out.risk_features, [c.baselines[k] for k in RISK_SIGNALS])
            behavior_baseline = [c.baselines[k] for k in BEHAVIOR_SIGNALS] + [c.baselines["demand_score"]]
            behavior_contrib = stage_contributions(c.behavior.predict, out.behavior_features, behavior_baseline)
            failure_contrib, failure_bias = c.failure.contributions(out.failure_features)

        results = [
            self._assemble(i, records[i], out, names, impacts[i], float(baseline_scores[i]), risk_contrib[i],
                           behavior_contrib[i], failure_contrib[i], float(failure_bias[i]))
            for i in range(len(records))
        ]
        if rank:
            ranks = rank_by_failure([r["scores"]["failure_raw"] for r in results])
            for result, rank_ in zip(results, ranks):
                result["priority_rank"] = rank_
            results.sort(key=lambda r: r["priority_rank"])
        return results

    def _assemble(self, i, record, out: StageOutputs, signal_names, impact_row, baseline_score, risk_c,
                  behavior_c, failure_c, failure_bias) -> dict:
        c = self.cascade
        risk, demand, behavior, failure = (float(a[i]) for a in (out.risk, out.demand, out.behavior, out.failure_raw))
        d: DemandResult = out.demand_details[i]
        percentile = priority_percentile(failure, c.reference_failure)
        band = band_for(failure)

        active = [s >= STAGE_ACTIVE_THRESHOLD for s in (risk, demand, behavior, failure)]
        current = max((n for n, is_active in enumerate(active, start=1) if is_active), default=0)
        if current:
            stage_name, stage_desc = _STAGE_NAMES[current]
        else:
            stage_name, stage_desc = "STABLE", "No cascade stage is active"

        def rows(names, values, impacts):
            return [
                {"signal": n, "label": SIGNAL_LABELS.get(n, n), "value": _r(v), "impact": _r(m)}
                for n, v, m in zip(names, values, impacts)
            ]

        stage_rows = [
            {"stage": 1, "score": risk, "active": active[0], "detail": None,
             "unit": "probability points (Shapley) vs. a healthy company",
             "contributions": rows(RISK_SIGNALS, out.risk_features[i], risk_c)},
            {"stage": 2, "score": demand, "active": active[1], "unit": None, "contributions": [],
             "detail": {
                 "method": "one-sided CUSUM on weekly job postings",
                 "change_detected": d.change_detected,
                 "change_week": d.change_week,
                 "baseline_weekly_postings": _r(d.baseline_mean, 2),
                 "recent_weekly_postings": None if d.recent_mean is None else _r(d.recent_mean, 2),
                 "drop_fraction": _r(d.drop_fraction),
             }},
            {"stage": 3, "score": behavior, "active": active[2], "detail": None,
             "unit": "probability points (Shapley) vs. a healthy company",
             "contributions": rows((*BEHAVIOR_SIGNALS, "demand_score"), out.behavior_features[i], behavior_c)},
            {"stage": 4, "score": failure, "active": active[3],
             "unit": "log-odds contribution (XGBoost); contributions + bias = margin, sigmoid(margin) = score",
             "detail": {"bias": _r(failure_bias)},
             "contributions": rows(c.failure.feature_names, out.failure_features[i], failure_c)},
            {"stage": 5, "score": percentile, "active": band != "GREEN", "unit": None, "contributions": [],
             "detail": {"band": band, "failure_raw_score": _r(failure),
                        "note": "score is the percentile of Failure_raw_score within the reference population"}},
        ]
        for row in stage_rows:
            row["name"], row["description"] = _STAGE_NAMES[row["stage"]]
            row["score"] = _r(row["score"])

        values = {k: record[k] for k in BEHAVIOR_SIGNALS + RISK_SIGNALS + ("client_churn", "delays")}
        impact_rows = [
            {
                "signal": name,
                "label": SIGNAL_LABELS[name],
                "detail": describe_signal(name, values.get(name), d),
                "impact": _r(impact),
            }
            for name, impact in zip(signal_names, impact_row)
        ]
        impact_rows.sort(key=lambda r: -r["impact"])
        drivers = [r["detail"] for r in impact_rows if r["impact"] >= _MIN_DRIVER_IMPACT][:3]
        summary = (
            f"{band}: failure score {failure:.2f}, higher than {percentile:.0%} of the reference population. "
            + (f"Main drivers: {'; '.join(drivers)}." if drivers else "No single signal stands out.")
        )

        return {
            "name": record.get("name"),
            "current_stage": {"number": current, "name": stage_name, "description": stage_desc},
            "scores": {
                "risk": _r(risk), "demand": _r(demand), "behavior": _r(behavior),
                "failure_raw": _r(failure), "priority_percentile": _r(percentile),
            },
            "band": band,
            "priority_rank": None,
            "recommended_actions": actions_for(band),
            "breakdown": {
                "summary": summary,
                "baseline_failure_score": _r(baseline_score),
                "stages": stage_rows,
                "signal_impact": impact_rows,
            },
        }
