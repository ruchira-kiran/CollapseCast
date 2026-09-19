"""Explainability: which signals caused what.

Attribution uses exact Shapley values, which have the property that matters for a dashboard: the
contributions *add up*. For a company, the value function is "the score when the signals in a
coalition keep their actual values and every other signal sits at its healthy baseline" (median of
surviving companies; for job postings, a flat series at the company's own baseline level, i.e. no
decline). With at most 8 players that is at most 256 coalitions, evaluated in one stacked pass.

* End-to-end signal impact (``signal_impacts``): Shapley over all 8 raw signals through the WHOLE
  cascade, in Failure_raw_score points. sum(impacts) == Failure_raw_score - baseline score, so
  effects that travel through several stages, and correlated signals that would mask each other in a
  one-at-a-time test, are still shared out fairly.
* Per-stage contributions (``stage_contributions``): the same idea applied to a single Random Forest
  stage's inputs, in probability points. The XGBoost stage instead reports the booster's exact
  per-feature contributions in log-odds, see ``FailureModel.contributions``.
"""
from __future__ import annotations

from math import factorial
from collections.abc import Callable, Sequence

import numpy as np

from app.config import POSTINGS_SIGNAL, SCALAR_SIGNALS, SIGNAL_LABELS
from app.data.batch import SignalBatch
from app.ml.demand import DemandResult, flat_series_like
from app.pipeline.cascade import Cascade


def _coalition_matrix(p: int) -> np.ndarray:
    """(2**p, p) boolean matrix; row m is the coalition whose members are the set bits of m."""
    return ((np.arange(2**p)[:, None] >> np.arange(p)[None, :]) & 1).astype(bool)


def shapley_from_values(f: np.ndarray, p: int) -> np.ndarray:
    """Exact Shapley values from coalition values.

    ``f`` has shape (2**p, n) with f[m] the value of coalition m (bit j set = player j present).
    Returns (n, p); each row sums to f[2**p - 1] - f[0].
    """
    masks = np.arange(2**p)
    sizes = _coalition_matrix(p).sum(axis=1)
    phi = np.zeros((f.shape[1], p))
    for j in range(p):
        without = masks[((masks >> j) & 1) == 0]
        s = sizes[without]
        weight = np.array([factorial(k) * factorial(p - k - 1) / factorial(p) for k in s])
        phi[:, j] = (weight[:, None] * (f[without | (1 << j)] - f[without])).sum(axis=0)
    return phi


def stage_contributions(
    predict: Callable[[np.ndarray], np.ndarray],
    X: np.ndarray,
    baseline: Sequence[float],
) -> np.ndarray:
    """(n, n_features) Shapley contributions of each input to ``predict``, relative to ``baseline``.

    Each row sums to predict(X[i]) - predict(baseline).
    """
    X = np.asarray(X, dtype=float)
    n, p = X.shape
    masks = _coalition_matrix(p)
    stacked = np.where(masks[:, None, :], X[None, :, :], np.asarray(baseline, dtype=float)[None, None, :])
    f = predict(stacked.reshape(-1, p)).reshape(2**p, n)
    return shapley_from_values(f, p)


def signal_impacts(cascade: Cascade, batch: SignalBatch) -> tuple[tuple[str, ...], np.ndarray, np.ndarray]:
    """End-to-end Shapley impact of each raw signal on Failure_raw_score.

    Returns (signal names, impacts of shape (n_companies, n_signals), baseline_score of shape
    (n_companies,)), where baseline_score is the failure score of the all-healthy counterfactual.
    Each company's impacts sum to its Failure_raw_score minus its baseline_score.
    """
    names = SCALAR_SIGNALS + (POSTINGS_SIGNAL,)
    p, n = len(names), len(batch)
    masks = _coalition_matrix(p)

    scalars = {
        k: np.where(masks[:, j][:, None], batch.scalars[k][None, :], cascade.baselines[k]).reshape(-1)
        for j, k in enumerate(SCALAR_SIGNALS)
    }
    # Reuse the same array objects across coalitions so Cascade.score computes CUSUM only once each.
    flat = [flat_series_like(series) for series in batch.postings]
    postings_bit = names.index(POSTINGS_SIGNAL)
    postings: list[np.ndarray] = []
    for m in range(2**p):
        postings.extend(batch.postings if masks[m, postings_bit] else flat)

    failure = cascade.score(SignalBatch(scalars, postings)).failure_raw.reshape(2**p, n)
    return names, shapley_from_values(failure, p), failure[0]


def describe_signal(name: str, value: float | None, demand: DemandResult) -> str:
    """Plain-language description of a raw signal's state for one company."""
    if name == POSTINGS_SIGNAL:
        if demand.change_detected:
            return f"job postings down {demand.drop_fraction:.0%} from baseline since week {demand.change_week}"
        return "job postings stable versus baseline"
    return f"{SIGNAL_LABELS[name]} = {value:.2f}"
