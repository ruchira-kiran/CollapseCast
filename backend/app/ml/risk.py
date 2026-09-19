"""Stage 1 - RISK: hiring_freeze_score, exec_departure_rate, news_negativity -> Risk_score (0-1).

Default: Random Forest classifier, Risk_score = P(collapse).

Cold-start fallback (documented, opt-in): with zero labeled history there is nothing to supervise
a Random Forest with, so ``mode="isolation_forest"`` fits an unsupervised Isolation Forest on the
three signals instead. Risk_score is then the *percentile* of the company's anomaly score within the
training population (0 = most typical, 1 = most anomalous). Select it with
``COLLAPSECAST_RISK_MODE=isolation_forest``. The model also drops to this mode by itself, with a
warning, if the Random Forest is requested but the labels are unusable (one class only, or fewer
than ``MIN_POSITIVES`` collapsed examples).

Caveats of the fallback:
  * Isolation Forest flags *unusual* companies, not *distressed* ones - an implausibly healthy
    company is also an outlier. Treat its scores as a triage heuristic until labels exist.
  * It only covers stage 1. Stages 3 and 4 are supervised and still need labels (or the synthetic set).
"""
from __future__ import annotations

import logging

import numpy as np
from sklearn.ensemble import IsolationForest

from app.config import RISK_SIGNALS
from app.ml.base import ForestScorer

logger = logging.getLogger(__name__)

MODES = ("random_forest", "isolation_forest")


class RiskModel(ForestScorer):
    feature_names = RISK_SIGNALS
    MIN_POSITIVES = 10

    def __init__(self, mode: str = "random_forest", **kwargs):
        if mode not in MODES:
            raise ValueError(f"risk mode must be one of {MODES}, got {mode!r}")
        super().__init__(**kwargs)
        self._kwargs["mode"] = mode  # so fresh() reproduces the requested mode
        self.requested_mode = mode
        self.mode = mode  # effective mode, settled in fit()
        self._iforest: IsolationForest | None = None
        self._reference: np.ndarray | None = None

    def fit(self, X, y=None):
        X = np.asarray(X, dtype=float)
        usable = (
            y is not None
            and len(np.unique(y)) == 2
            and int(np.sum(np.asarray(y) == 1)) >= self.MIN_POSITIVES
        )
        if self.requested_mode == "random_forest" and not usable:
            logger.warning("No usable labels for the Random Forest risk model - falling back to Isolation Forest.")
        self.mode = "random_forest" if self.requested_mode == "random_forest" and usable else "isolation_forest"

        if self.mode == "random_forest":
            return super().fit(X, y)

        self._iforest = IsolationForest(n_estimators=200, random_state=self.seed, n_jobs=1).fit(X)
        self._reference = np.sort(-self._iforest.score_samples(X))
        return self

    def predict(self, X) -> np.ndarray:
        if self.mode == "random_forest":
            return super().predict(X)
        anomaly = -self._iforest.score_samples(np.asarray(X, dtype=float))
        return np.searchsorted(self._reference, anomaly, side="right") / len(self._reference)
