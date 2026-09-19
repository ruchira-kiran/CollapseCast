import pytest

from app.pipeline.resources import actions_for, band_for, rank_by_failure


@pytest.mark.parametrize(
    "score, band",
    [
        (1.00, "RED"), (0.80, "RED"),
        (0.7999, "ORANGE"), (0.50, "ORANGE"),
        (0.4999, "YELLOW"), (0.30, "YELLOW"),
        (0.2999, "GREEN"), (0.0, "GREEN"),
    ],
)
def test_band_thresholds(score, band):
    assert band_for(score) == band


@pytest.mark.parametrize("band", ["RED", "ORANGE", "YELLOW", "GREEN"])
def test_every_band_has_actions_for_all_three_audiences(band):
    actions = actions_for(band)
    assert set(actions) == {"Employees", "Investors", "HR"}
    assert all(actions[audience] for audience in actions)


def test_rank_by_failure_orders_highest_first():
    assert rank_by_failure([0.2, 0.9, 0.5]) == [3, 1, 2]
