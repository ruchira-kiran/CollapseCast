import numpy as np
import pytest

from app.data.loader import load_dataset
from app.ml.risk import RiskModel


def test_isolation_forest_fallback_trains_with_zero_labels():
    X = load_dataset().batch.matrix(RiskModel.feature_names)
    model = RiskModel(mode="isolation_forest").fit(X, None)
    scores = model.predict(X)
    assert model.mode == "isolation_forest"
    assert scores.min() >= 0.0 and scores.max() <= 1.0


def test_random_forest_request_without_usable_labels_falls_back():
    X = load_dataset().batch.matrix(RiskModel.feature_names)
    model = RiskModel(mode="random_forest").fit(X, np.zeros(len(X), dtype=int))
    assert model.mode == "isolation_forest"


def test_unknown_risk_mode_is_rejected():
    with pytest.raises(ValueError):
        RiskModel(mode="nope")


def test_out_of_fold_scores_are_valid_probabilities():
    ds = load_dataset()
    X = ds.batch.matrix(RiskModel.feature_names)
    oof = RiskModel().oof_scores(X, ds.collapsed)
    assert oof.shape == (len(X),)
    assert oof.min() >= 0.0 and oof.max() <= 1.0
