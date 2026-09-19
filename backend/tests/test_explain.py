import numpy as np
import pytest

from app.config import SCALAR_SIGNALS
from app.data.batch import SignalBatch
from app.pipeline.explain import shapley_from_values, signal_impacts, stage_contributions


def _values_for(fn, p):
    """Coalition-value table f[m] = fn(set of players in m), shape (2**p, 1)."""
    return np.array([[fn({j for j in range(p) if (m >> j) & 1})] for m in range(2**p)], dtype=float)


def test_shapley_recovers_the_weights_of_an_additive_game():
    weights = [0.5, -0.2, 0.1]
    phi = shapley_from_values(_values_for(lambda s: sum(weights[j] for j in s), 3), 3)
    np.testing.assert_allclose(phi[0], weights, atol=1e-12)


def test_shapley_splits_an_interaction_evenly_and_sums_to_the_total():
    # Value only exists when players 0 AND 1 are both present: they share it; player 2 is a null player.
    phi = shapley_from_values(_values_for(lambda s: 1.0 if {0, 1} <= s else 0.0, 3), 3)
    np.testing.assert_allclose(phi[0], [0.5, 0.5, 0.0], atol=1e-12)


def test_stage_contributions_sum_to_score_minus_baseline_score(engine):
    cascade = engine.cascade
    X = np.array([[0.9, 0.5, 0.8], [0.2, 0.1, 0.3]])
    baseline = [cascade.baselines[k] for k in cascade.risk.feature_names]
    phi = stage_contributions(cascade.risk.predict, X, baseline)
    expected = cascade.risk.predict(X) - cascade.risk.predict(np.array([baseline]))[0]
    np.testing.assert_allclose(phi.sum(axis=1), expected, atol=1e-9)


def test_end_to_end_impacts_add_up_to_failure_score_minus_baseline(engine):
    batch = SignalBatch.from_records(engine.samples)
    out = engine.cascade.score(batch)
    names, impacts, baseline = signal_impacts(engine.cascade, batch)
    assert len(names) == len(SCALAR_SIGNALS) + 1
    np.testing.assert_allclose(impacts.sum(axis=1) + baseline, out.failure_raw, atol=1e-9)


def test_api_breakdown_is_additive_up_to_rounding(engine):
    for result in engine.analyze(engine.samples):
        b = result["breakdown"]
        total = b["baseline_failure_score"] + sum(i["impact"] for i in b["signal_impact"])
        assert total == pytest.approx(result["scores"]["failure_raw"], abs=1e-3)


def test_a_collapsing_postings_series_is_credited_in_the_impact(engine):
    worst = engine.analyze([engine.samples[-1]])[0]
    postings = next(i for i in worst["breakdown"]["signal_impact"] if i["signal"] == "weekly_job_postings")
    assert postings["impact"] > 0.005
