import numpy as np
import pytest

from app.config import SCALAR_SIGNALS


def test_cascade_learns_something_on_the_synthetic_data(engine):
    auc = engine.cascade.metrics["cv_auc"]
    assert auc["failure"] > 0.85
    assert auc["risk"] > 0.7 and auc["behavior"] > 0.7 and auc["demand"] > 0.65


def test_failure_stage_contributions_sum_to_the_margin(engine):
    cascade = engine.cascade
    X = np.array([[0.2, 0.0, 0.3, 0.1, 0.1], [0.9, 0.7, 0.8, 0.4, 0.6]])
    contribs, bias = cascade.failure.contributions(X)
    np.testing.assert_allclose(contribs.sum(axis=1) + bias, cascade.failure.margin(X), rtol=1e-4, atol=1e-4)


def test_failure_score_is_monotone_in_churn(engine):
    grid = np.array([[0.5, 0.3, 0.5, churn, 0.3] for churn in np.linspace(0, 1, 11)])
    assert np.all(np.diff(engine.cascade.failure.predict(grid)) >= -1e-9)


def test_sample_companies_span_the_bands_in_severity_order(engine):
    results = engine.analyze(engine.samples)
    failure = [r["scores"]["failure_raw"] for r in results]
    assert results[0]["band"] == "GREEN"
    assert results[-1]["band"] in ("RED", "ORANGE")
    assert failure == sorted(failure)  # the engine serves samples healthiest-first
    assert {r["band"] for r in results} == {"GREEN", "YELLOW", "ORANGE", "RED"}


def test_result_shape_and_explanations(engine):
    result = engine.analyze([engine.samples[-1]])[0]
    assert set(result["scores"]) == {"risk", "demand", "behavior", "failure_raw", "priority_percentile"}
    assert [s["stage"] for s in result["breakdown"]["stages"]] == [1, 2, 3, 4, 5]
    impacts = result["breakdown"]["signal_impact"]
    assert len(impacts) == len(SCALAR_SIGNALS) + 1
    assert [i["impact"] for i in impacts] == sorted((i["impact"] for i in impacts), reverse=True)
    assert impacts[0]["impact"] > 0.05  # the worst demo company must have at least one real driver
    assert result["recommended_actions"]["Employees"]


def test_batch_is_sorted_by_failure_score_with_ranks(engine):
    shuffled = [engine.samples[i] for i in (3, 7, 0, 5)]
    results = engine.analyze(shuffled, rank=True)
    scores = [r["scores"]["failure_raw"] for r in results]
    assert scores == sorted(scores, reverse=True)
    assert [r["priority_rank"] for r in results] == [1, 2, 3, 4]


def test_identical_request_gives_identical_result(engine):
    assert engine.analyze([engine.samples[4]]) == engine.analyze([engine.samples[4]])
