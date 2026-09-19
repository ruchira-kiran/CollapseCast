import numpy as np
import pytest

from app.ml.demand import cusum_demand, flat_series_like


def test_stable_series_has_no_change_and_zero_score():
    result = cusum_demand([40, 41, 39, 40, 42, 38, 40, 41, 39, 40, 41, 40, 39, 41, 40, 40])
    assert not result.change_detected
    assert result.score == 0.0
    assert result.change_week is None


def test_step_drop_is_detected_near_its_start_with_matching_magnitude():
    series = [40] * 12 + [16] * 10  # 60% drop from week 13 (1-based)
    result = cusum_demand(series)
    assert result.change_detected
    assert result.change_week == 13
    assert result.score == pytest.approx(0.6, abs=0.02)


def test_increase_is_not_flagged_as_a_drop():
    result = cusum_demand([20] * 10 + [45] * 10)
    assert not result.change_detected
    assert result.score == 0.0


def test_score_is_always_within_unit_interval():
    result = cusum_demand([50] * 10 + [0] * 10)
    assert result.change_detected
    assert 0.0 <= result.score <= 1.0


def test_too_short_series_is_rejected():
    with pytest.raises(ValueError):
        cusum_demand([10] * 5)


def test_flat_counterfactual_never_triggers():
    series = np.array([40] * 8 + [10] * 12)
    assert not cusum_demand(flat_series_like(series)).change_detected
