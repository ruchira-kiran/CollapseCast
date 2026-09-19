"""Stage 5 - RESOURCES: no ML. Sort by Failure_raw_score, band it, attach recommended actions.

    >= 0.80  RED       0.50-0.79  ORANGE       0.30-0.49  YELLOW       < 0.30  GREEN
"""
from __future__ import annotations

import numpy as np

from app.config import BAND_THRESHOLDS, DEFAULT_BAND


def band_for(failure_raw_score: float) -> str:
    for band, threshold in BAND_THRESHOLDS:
        if failure_raw_score >= threshold:
            return band
    return DEFAULT_BAND


def priority_percentile(score: float, reference_sorted: np.ndarray) -> float:
    """Share of the reference population scoring at or below ``score`` (1.0 = riskier than all of it)."""
    if len(reference_sorted) == 0:
        return 0.0
    return float(np.searchsorted(reference_sorted, score, side="right") / len(reference_sorted))


def rank_by_failure(scores) -> list[int]:
    """1-based priority rank of each score (1 = highest Failure_raw_score); ties keep input order."""
    order = sorted(range(len(scores)), key=lambda i: -scores[i])
    ranks = [0] * len(scores)
    for rank, i in enumerate(order, start=1):
        ranks[i] = rank
    return ranks


RECOMMENDED_ACTIONS: dict[str, dict[str, list[str]]] = {
    "RED": {
        "Employees": [
            "Start an active job search now; do not wait for an announcement.",
            "Build a 3-6 month expense cushion and avoid new large financial commitments.",
            "Get pending salary, reimbursements and PF/gratuity status confirmed in writing.",
        ],
        "Investors": [
            "Pause follow-on funding and new tranches until liquidity is independently verified.",
            "Invoke information and board-observer rights; request a 13-week cash-flow forecast.",
            "Prepare for restructuring or a write-down, and check your position in the liquidation order.",
        ],
        "HR": [
            "Activate the contingency workforce plan and brief leadership on the timeline.",
            "Have legal review notice periods, severance, gratuity and PF obligations before any action.",
            "Prepare outplacement and redeployment support; agree a retention plan for critical roles only.",
        ],
    },
    "ORANGE": {
        "Employees": [
            "Update your resume and quietly explore the market.",
            "Ask managers for candid clarity on runway, funding and the roadmap.",
            "Document your work and keep copies of your contracts and pay records.",
        ],
        "Investors": [
            "Request an out-of-cycle financial review and updated runway numbers.",
            "Set milestone-based conditions on any further capital.",
            "Stress-test the position against a 30-50% revenue decline.",
        ],
        "HR": [
            "Freeze non-critical hiring and review backfills.",
            "Model workforce-cost scenarios and identify the critical-talent list.",
            "Increase communication cadence and monitor attrition and engagement weekly.",
        ],
    },
    "YELLOW": {
        "Employees": [
            "Stay alert to changes in leadership, hiring and payment timelines.",
            "Keep your skills and network current.",
            "Raise concerns with your manager and track responses.",
        ],
        "Investors": [
            "Move the company to the watchlist and increase reporting frequency.",
            "Ask management to explain the leading indicators that are deteriorating.",
            "Re-check covenants and follow-on assumptions next quarter.",
        ],
        "HR": [
            "Run a pulse survey and act on the drivers of falling engagement.",
            "Review executive retention and succession for key leaders.",
            "Prepare a light contingency plan without triggering alarm.",
        ],
    },
    "GREEN": {
        "Employees": [
            "No action needed; continue normal career planning.",
        ],
        "Investors": [
            "Continue standard periodic monitoring.",
        ],
        "HR": [
            "Maintain regular engagement and attrition tracking.",
        ],
    },
}


def actions_for(band: str) -> dict[str, list[str]]:
    return {audience: list(items) for audience, items in RECOMMENDED_ACTIONS[band].items()}
