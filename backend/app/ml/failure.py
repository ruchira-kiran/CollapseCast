"""Stage 4 - FAILURE: XGBoost fusing the upstream scores with client churn and delays.

Inputs:  Risk_score, Demand_score, Behavior_score, client_churn, delays
Output:  Failure_raw_score = sigmoid(margin), where margin is the booster's raw log-odds output.

Monotone constraints (every input may only push the score up) keep the fused model sane on a small
training set and make its explanations unambiguous: more churn can never *lower* the failure score.
"""
from __future__ import annotations

import numpy as np
import xgboost as xgb

from app.config import FAILURE_SIGNALS, RANDOM_SEED
from app.ml.base import oof_scores, sigmoid


class FailureModel:
    feature_names = ("risk_score", "demand_score", "behavior_score", *FAILURE_SIGNALS)

    def __init__(self, *, seed: int = RANDOM_SEED):
        self.seed = seed
        self._model = xgb.XGBClassifier(
            n_estimators=150,
            max_depth=3,
            learning_rate=0.08,
            subsample=0.9,
            colsample_bytree=0.9,
            min_child_weight=2,
            monotone_constraints="(" + ",".join("1" for _ in self.feature_names) + ")",
            eval_metric="logloss",
            tree_method="hist",
            n_jobs=1,
            random_state=seed,
            verbosity=0,
        )

    def fit(self, X, y):
        self._model.fit(np.asarray(X, dtype=np.float32), np.asarray(y))
        return self

    @staticmethod
    def _dmatrix(X) -> xgb.DMatrix:
        return xgb.DMatrix(np.asarray(X, dtype=np.float32))

    def margin(self, X) -> np.ndarray:
        return self._model.get_booster().predict(self._dmatrix(X), output_margin=True)

    def predict(self, X) -> np.ndarray:
        """Failure_raw_score in [0, 1]."""
        return sigmoid(self.margin(X))

    def contributions(self, X) -> tuple[np.ndarray, np.ndarray]:
        """Exact per-feature contributions to the margin (log-odds), plus the bias term.

        Returns (contribs of shape (n, n_features), bias of shape (n,)); each row of
        contribs.sum(axis=1) + bias equals margin(X).
        """
        raw = self._model.get_booster().predict(self._dmatrix(X), pred_contribs=True)
        return raw[:, :-1], raw[:, -1]

    def fresh(self) -> "FailureModel":
        return FailureModel(seed=self.seed)

    def oof_scores(self, X, y) -> np.ndarray:
        return oof_scores(self.fresh, X, y, seed=self.seed)
