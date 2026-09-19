"""Stage 3 - BEHAVIOR: review_sentiment, engagement_signals and Demand_score -> Behavior_score.

Random Forest classifier, Behavior_score = P(collapse). Demand_score (stage 2's output) is the
third feature, which is what chains the stages together.
"""
from __future__ import annotations

from app.config import BEHAVIOR_SIGNALS
from app.ml.base import ForestScorer


class BehaviorModel(ForestScorer):
    feature_names = (*BEHAVIOR_SIGNALS, "demand_score")
