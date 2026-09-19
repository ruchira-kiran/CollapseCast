"""Shared model plumbing: out-of-fold scoring, the sigmoid, and a Random Forest wrapper."""
from __future__ import annotations

from typing import Callable

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import KFold, StratifiedKFold

from app.config import RANDOM_SEED


def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.asarray(z, dtype=float)))


def oof_scores(make_model: Callable[[], object], X: np.ndarray, y, n_splits: int = 5, seed: int = RANDOM_SEED):
    """Out-of-fold scores: every row is scored by a model that never saw it.

    Later cascade stages are trained on these instead of in-sample outputs, otherwise a forest
    that memorized the training labels would look near-perfect and the next stage would learn to
    over-trust it.
    """
    X = np.asarray(X, dtype=float)
    if y is not None:
        y = np.asarray(y)
        stratify = np.bincount(y, minlength=2).min() >= n_splits
    else:
        stratify = False
    splitter = (StratifiedKFold if stratify else KFold)(n_splits=n_splits, shuffle=True, random_state=seed)

    out = np.zeros(len(X))
    for train, valid in splitter.split(X, y if stratify else None):
        model = make_model()
        model.fit(X[train], None if y is None else y[train])
        out[valid] = model.predict(X[valid])
    return out


class ForestScorer:
    """Random Forest that maps a feature matrix to P(collapse) in [0, 1]."""

    feature_names: tuple[str, ...] = ()

    def __init__(self, *, seed: int = RANDOM_SEED, n_estimators: int = 150, min_samples_leaf: int = 5):
        self.seed = seed
        self._kwargs = {"seed": seed, "n_estimators": n_estimators, "min_samples_leaf": min_samples_leaf}
        # min_samples_leaf > 1 keeps probabilities smooth instead of snapping to 0/1.
        self._forest = RandomForestClassifier(
            n_estimators=n_estimators, min_samples_leaf=min_samples_leaf, random_state=seed, n_jobs=1
        )

    def fit(self, X, y):
        y = np.asarray(y)
        if len(np.unique(y)) < 2:
            raise ValueError(f"{type(self).__name__} needs both collapsed and survived examples to train")
        self._forest.fit(np.asarray(X, dtype=float), y)
        return self

    def predict(self, X) -> np.ndarray:
        return self._forest.predict_proba(np.asarray(X, dtype=float))[:, 1]

    def fresh(self):
        return type(self)(**self._kwargs)

    def oof_scores(self, X, y) -> np.ndarray:
        return oof_scores(self.fresh, X, y, seed=self.seed)
