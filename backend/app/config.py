"""Central configuration: paths, signal definitions, band thresholds, stage metadata."""
from __future__ import annotations

import os
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
COMPANIES_CSV = DATA_DIR / "companies.csv"
POSTINGS_CSV = DATA_DIR / "job_postings_weekly.csv"
SAMPLES_JSON = DATA_DIR / "sample_companies.json"

RANDOM_SEED = 42

# "random_forest" (default) or "isolation_forest" (zero-label cold-start fallback for stage 1).
RISK_MODE = os.getenv("COLLAPSECAST_RISK_MODE", "random_forest").strip().lower()

# Comma-separated list of allowed origins for the React frontend. "*" allows any origin
# (no cookies/credentials are used, so this is safe for a demo); tighten it for production,
# e.g. CORS_ORIGINS=https://main.d1234abcd.amplifyapp.com
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]

# --- Signals -----------------------------------------------------------------------------
RISK_SIGNALS = ("hiring_freeze_score", "exec_departure_rate", "news_negativity")
BEHAVIOR_SIGNALS = ("review_sentiment", "engagement_signals")
FAILURE_SIGNALS = ("client_churn", "delays")
SCALAR_SIGNALS = RISK_SIGNALS + BEHAVIOR_SIGNALS + FAILURE_SIGNALS
POSTINGS_SIGNAL = "weekly_job_postings"
ALL_SIGNALS = SCALAR_SIGNALS + (POSTINGS_SIGNAL,)

SIGNAL_LABELS = {
    "hiring_freeze_score": "Hiring freeze",
    "exec_departure_rate": "Executive departures",
    "news_negativity": "Negative news",
    "review_sentiment": "Employee review sentiment",
    "engagement_signals": "Engagement",
    "client_churn": "Client churn",
    "delays": "Delivery / payment delays",
    "weekly_job_postings": "Job-posting demand",
    "risk_score": "Risk score",
    "demand_score": "Demand score",
    "behavior_score": "Behavior score",
}

# --- Stages ------------------------------------------------------------------------------
STAGES = (
    (1, "RISK", "Leadership and hiring stress"),
    (2, "DEMAND", "Decline in job-posting demand"),
    (3, "BEHAVIOR", "Employee and customer behavior"),
    (4, "FAILURE", "Fused probability of failure"),
    (5, "RESOURCES", "Priority band and recommended actions"),
)

# A stage 1-4 score at or above this marks the stage as "active" for that company.
# The company's current stage is the deepest active stage (0 = none active).
STAGE_ACTIVE_THRESHOLD = 0.5

# --- Stage 5 bands (Failure_raw_score) ---------------------------------------------------
BAND_THRESHOLDS = (("RED", 0.80), ("ORANGE", 0.50), ("YELLOW", 0.30))
DEFAULT_BAND = "GREEN"
