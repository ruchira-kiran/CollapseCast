"""Stage 2 - DEMAND: CUSUM change-point detection on weekly job-posting counts.

No training involved. The first ``BASELINE_WEEKS`` weeks define "normal"; a one-sided (downward)
CUSUM then runs over the remaining weeks:

    S_t = max(0, S_{t-1} + (mu0 - x_t) / sigma - k)        alarm when S_t > h

``sigma`` is the baseline standard deviation, floored at sqrt(mu0) because counts are Poisson-like
and eight samples give a noisy sigma estimate. With the textbook k = 0.5 and h = 5 the false-alarm
rate on a stable series is low, and a spurious alarm still yields a tiny score (see below).

Demand_score is the normalized drop magnitude: if an alarm fires, the fractional decline of the mean
posting count from the estimated change point to the end of the series relative to the baseline
mean, clipped to [0, 1]. No alarm means no statistically supported decline, so the score is 0.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

BASELINE_WEEKS = 8
MIN_WEEKS = 12
CUSUM_K = 0.5
CUSUM_H = 5.0


@dataclass(frozen=True)
class DemandResult:
    score: float  # Demand_score in [0, 1]
    change_detected: bool
    change_week: int | None  # 1-based week the decline is estimated to have started
    baseline_mean: float
    recent_mean: float | None  # mean postings from the change point to the last week
    drop_fraction: float  # 0 when no change was detected


def cusum_demand(
    postings,
    *,
    baseline_weeks: int = BASELINE_WEEKS,
    k: float = CUSUM_K,
    h: float = CUSUM_H,
    min_weeks: int = MIN_WEEKS,
) -> DemandResult:
    x = np.asarray(postings, dtype=float)
    if x.ndim != 1 or x.size < max(min_weeks, baseline_weeks + 1):
        raise ValueError(f"need a 1-D series of at least {max(min_weeks, baseline_weeks + 1)} weekly counts")

    baseline = x[:baseline_weeks]
    mu = float(baseline.mean())
    sigma = max(float(baseline.std(ddof=1)), float(np.sqrt(max(mu, 1.0))))

    s = 0.0
    start = baseline_weeks  # 0-based index of the first week after the last time S was 0
    alarm = False
    for t in range(baseline_weeks, x.size):
        s = max(0.0, s + (mu - x[t]) / sigma - k)
        if s == 0.0:
            start = t + 1
        elif s > h:
            alarm = True
            break

    if not alarm or mu <= 0.0:
        return DemandResult(0.0, False, None, mu, None, 0.0)

    recent = float(x[start:].mean())
    drop = float(np.clip((mu - recent) / mu, 0.0, 1.0))
    return DemandResult(drop, True, start + 1, mu, recent, drop)


def flat_series_like(postings, baseline_weeks: int = BASELINE_WEEKS) -> np.ndarray:
    """A 'no decline' counterfactual: the company's own baseline level held constant."""
    x = np.asarray(postings, dtype=float)
    return np.full(x.shape, x[:baseline_weeks].mean())
