"""Load the synthetic training set and the demo sample companies from disk."""
from __future__ import annotations

import csv
import json
import logging
from collections import defaultdict
from dataclasses import dataclass

import numpy as np

from app.config import COMPANIES_CSV, POSTINGS_CSV, SAMPLES_JSON, SCALAR_SIGNALS
from app.data.batch import SignalBatch

logger = logging.getLogger(__name__)


@dataclass
class Dataset:
    company_ids: list[str]
    batch: SignalBatch
    collapsed: np.ndarray  # int 0/1 labels


def ensure_data() -> None:
    """Generate the synthetic files if they are missing (e.g. a fresh checkout)."""
    if COMPANIES_CSV.exists() and POSTINGS_CSV.exists() and SAMPLES_JSON.exists():
        return
    from app.data.generate_synthetic import generate

    logger.info("Synthetic data not found - generating it into %s", COMPANIES_CSV.parent)
    generate(n=600, seed=42, out_dir=COMPANIES_CSV.parent)


def load_dataset() -> Dataset:
    ensure_data()

    weekly: dict[str, list[tuple[int, float]]] = defaultdict(list)
    with POSTINGS_CSV.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            weekly[row["company_id"]].append((int(row["week"]), float(row["postings"])))

    ids: list[str] = []
    rows: list[dict[str, str]] = []
    with COMPANIES_CSV.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            ids.append(row["company_id"])
            rows.append(row)

    postings = [np.array([p for _, p in sorted(weekly[cid])], dtype=float) for cid in ids]
    scalars = {k: np.array([float(r[k]) for r in rows], dtype=float) for k in SCALAR_SIGNALS}
    collapsed = np.array([int(r["collapsed"]) for r in rows], dtype=int)
    return Dataset(ids, SignalBatch(scalars, postings), collapsed)


def load_samples() -> list[dict]:
    """Demo companies: raw-signal dicts in the same shape the /predict endpoint accepts."""
    ensure_data()
    return json.loads(SAMPLES_JSON.read_text(encoding="utf-8"))
