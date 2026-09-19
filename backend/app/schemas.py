"""Request and response models for the CollapseCast API."""
from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

Band = Literal["RED", "ORANGE", "YELLOW", "GREEN"]
WeeklyCount = Annotated[int, Field(ge=0, le=1_000_000)]


class CompanySignals(BaseModel):
    """Raw signals for one company. Unknown extra fields (e.g. ``sector``) are ignored."""

    name: str | None = Field(default=None, max_length=120, description="Optional display name.")
    hiring_freeze_score: float = Field(ge=0, le=1, description="0 = hiring normally, 1 = complete hiring freeze.")
    exec_departure_rate: float = Field(ge=0, le=1, description="Share of senior executives who left in the last 12 months.")
    news_negativity: float = Field(ge=0, le=1, description="0 = neutral or positive coverage, 1 = uniformly negative.")
    review_sentiment: float = Field(ge=-1, le=1, description="Employee-review sentiment: -1 very negative, +1 very positive.")
    engagement_signals: float = Field(ge=0, le=1, description="Employee/product engagement: 1 = healthy, 0 = disengaged.")
    client_churn: float = Field(ge=0, le=1, description="Share of clients lost over the trailing 6 months.")
    delays: float = Field(ge=0, le=1, description="Severity of delivery and payment delays: 0 none, 1 severe.")
    weekly_job_postings: list[WeeklyCount] = Field(
        min_length=12,
        max_length=104,
        description="Open job postings per week, oldest first. The first 8 weeks are treated as the baseline.",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Example Co",
                "hiring_freeze_score": 0.72,
                "exec_departure_rate": 0.35,
                "news_negativity": 0.64,
                "review_sentiment": -0.35,
                "engagement_signals": 0.38,
                "client_churn": 0.28,
                "delays": 0.5,
                "weekly_job_postings": [42, 40, 44, 41, 43, 39, 42, 40, 36, 30, 27, 22, 20, 18, 15, 14, 12, 12, 10, 9],
            }
        }
    }


class SampleCompany(CompanySignals):
    name: str
    sector: str | None = None


class CurrentStage(BaseModel):
    number: int = Field(description="Deepest active stage among 1-4; 0 if none is active.")
    name: str
    description: str


class Scores(BaseModel):
    risk: float = Field(description="Stage 1 Risk_score, 0-1.")
    demand: float = Field(description="Stage 2 Demand_score, 0-1.")
    behavior: float = Field(description="Stage 3 Behavior_score, 0-1.")
    failure_raw: float = Field(description="Stage 4 Failure_raw_score, 0-1.")
    priority_percentile: float = Field(
        description="Stage 5: share of the reference population with a lower Failure_raw_score, 0-1."
    )


class Contribution(BaseModel):
    signal: str
    label: str
    value: float
    impact: float


class StageBreakdown(BaseModel):
    stage: int
    name: str
    description: str
    score: float
    active: bool
    unit: str | None = None
    detail: dict[str, Any] | None = None
    contributions: list[Contribution]


class SignalImpact(BaseModel):
    signal: str
    label: str
    detail: str
    impact: float = Field(
        description="Shapley contribution of this signal to Failure_raw_score, in score points. Can be slightly "
        "negative when the signal is better than the healthy baseline or through model noise/interactions."
    )


class Breakdown(BaseModel):
    summary: str
    baseline_failure_score: float = Field(
        description="Failure_raw_score of an all-healthy counterpart company. "
        "baseline_failure_score + sum(signal_impact[].impact) equals scores.failure_raw."
    )
    stages: list[StageBreakdown]
    signal_impact: list[SignalImpact] = Field(description="Sorted by impact, largest first.")


class PredictResponse(BaseModel):
    name: str | None
    current_stage: CurrentStage
    scores: Scores
    band: Band
    priority_rank: int | None = Field(default=None, description="1 = highest priority; only set by /predict/batch.")
    recommended_actions: dict[str, list[str]] = Field(description="Audience (Employees / Investors / HR) -> actions.")
    breakdown: Breakdown


class BatchRequest(BaseModel):
    companies: list[CompanySignals] = Field(min_length=1, max_length=100)


class BatchResponse(BaseModel):
    results: list[PredictResponse] = Field(description="Sorted by Failure_raw_score, highest first.")
