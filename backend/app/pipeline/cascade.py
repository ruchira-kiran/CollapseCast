"""The 5-stage cascade (stages 1-4 here; stage 5 lives in resources.py).

    1 RISK      RF on hiring_freeze / exec_departure / news_negativity        -> Risk_score
    2 DEMAND    CUSUM on weekly job postings                                  -> Demand_score
    3 BEHAVIOR  RF on review_sentiment / engagement / Demand_score            -> Behavior_score
    4 FAILURE   XGBoost on Risk, Demand, Behavior, client_churn, delays       -> Failure_raw_score

Each stage's output is an input to the next. When training, stages 3 and 4 receive *out-of-fold*
outputs of the stages before them (see ml.base.oof_scores), so they learn from realistic, not
memorized, upstream scores. At inference time the fully fitted models are used.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
from sklearn.metrics import roc_auc_score

from app.config import BEHAVIOR_SIGNALS, FAILURE_SIGNALS, RANDOM_SEED, RISK_MODE, RISK_SIGNALS, SCALAR_SIGNALS
from app.data.batch import SignalBatch
from app.ml.behavior import BehaviorModel
from app.ml.demand import DemandResult, cusum_demand
from app.ml.failure import FailureModel
from app.ml.risk import RiskModel

logger = logging.getLogger(__name__)


@dataclass
class StageOutputs:
    """Scores for every company in a batch, plus the feature matrices each stage saw."""

    risk: np.ndarray
    demand: np.ndarray
    behavior: np.ndarray
    failure_raw: np.ndarray
    demand_details: list[DemandResult]
    risk_features: np.ndarray
    behavior_features: np.ndarray
    failure_features: np.ndarray


class Cascade:
    def __init__(self, risk_mode: str = RISK_MODE, seed: int = RANDOM_SEED):
        self.seed = seed
        self.risk = RiskModel(mode=risk_mode, seed=seed)
        self.behavior = BehaviorModel(seed=seed)
        self.failure = FailureModel(seed=seed)
        # Median of every surviving company's signals: the "healthy" reference used for explanations.
        self.baselines: dict[str, float] = {}
        # Honest (out-of-fold) Failure_raw_scores of the training population, for percentile ranking.
        self.reference_failure: np.ndarray = np.array([])
        self.metrics: dict = {}

    # --- inference ------------------------------------------------------------------------
    def score(self, batch: SignalBatch) -> StageOutputs:
        risk_x = batch.matrix(RISK_SIGNALS)
        risk = self.risk.predict(risk_x)

        # Memoized by array identity: explain.py stacks many copies of the same few series.
        cache: dict[int, DemandResult] = {}
        details = [cache[id(p)] if id(p) in cache else cache.setdefault(id(p), cusum_demand(p)) for p in batch.postings]
        demand = np.array([d.score for d in details])

        behavior_x = np.column_stack([batch.matrix(BEHAVIOR_SIGNALS), demand])
        behavior = self.behavior.predict(behavior_x)

        failure_x = np.column_stack([risk, demand, behavior, batch.matrix(FAILURE_SIGNALS)])
        failure_raw = self.failure.predict(failure_x)
        return StageOutputs(risk, demand, behavior, failure_raw, details, risk_x, behavior_x, failure_x)

    # --- training -------------------------------------------------------------------------
    def fit(self, batch: SignalBatch, y) -> dict:
        y = np.asarray(y, dtype=int)

        demand = np.array([cusum_demand(p).score for p in batch.postings])
        risk_x = batch.matrix(RISK_SIGNALS)
        behavior_x = np.column_stack([batch.matrix(BEHAVIOR_SIGNALS), demand])

        risk_oof = self.risk.oof_scores(risk_x, y)
        behavior_oof = self.behavior.oof_scores(behavior_x, y)
        failure_x = np.column_stack([risk_oof, demand, behavior_oof, batch.matrix(FAILURE_SIGNALS)])
        failure_oof = self.failure.oof_scores(failure_x, y)

        self.risk.fit(risk_x, y)
        self.behavior.fit(behavior_x, y)
        self.failure.fit(failure_x, y)

        survivors = y == 0
        self.baselines = {k: float(np.median(batch.scalars[k][survivors])) for k in SCALAR_SIGNALS}
        self.baselines["demand_score"] = float(np.median(demand[survivors]))
        self.reference_failure = np.sort(failure_oof)

        self.metrics = {
            "training_companies": int(len(y)),
            "collapsed_share": round(float(y.mean()), 4),
            "risk_model": self.risk.mode,
            # Cross-validated AUCs on SYNTHETIC data: they show the wiring works, not real-world accuracy.
            "cv_auc": {
                "risk": round(float(roc_auc_score(y, risk_oof)), 4),
                "demand": round(float(roc_auc_score(y, demand)), 4),
                "behavior": round(float(roc_auc_score(y, behavior_oof)), 4),
                "failure": round(float(roc_auc_score(y, failure_oof)), 4),
            },
            "data": "synthetic",
        }
        logger.info("Cascade trained: %s", self.metrics)
        return self.metrics
