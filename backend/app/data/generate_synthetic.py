"""Synthetic training data for CollapseCast (there is no real labeled history yet).

Every company gets a latent distress ``severity`` in [0, 1]. Collapsed companies draw it from a
high-skewed Beta, survivors from a low-skewed Beta; the two overlap on purpose, so the models
face some genuinely ambiguous cases instead of a trivially separable toy set. All signals are
noisy functions of severity, and the weekly job-posting series gets a step-down (ramped over a few
weeks) with a probability that grows with severity.

Standard library only, so it also runs before the ML dependencies are installed.

Regenerate (from the backend/ directory):

    python -m app.data.generate_synthetic                # defaults: 600 companies, seed 42
    python -m app.data.generate_synthetic --n 1000 --seed 7

Outputs (in app/data/): companies.csv, job_postings_weekly.csv, sample_companies.json.
The sample companies are *not* part of the training set; they feed the dashboard's picker.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
from pathlib import Path

from app.config import COMPANIES_CSV, POSTINGS_CSV, SAMPLES_JSON, SCALAR_SIGNALS

WEEKS = 26
COLLAPSE_RATE = 0.30

SECTORS = ("SaaS", "Fintech", "EdTech", "Logistics", "Retail Tech", "HealthTech", "Mobility", "D2C")
NAME_HEAD = ("Aster", "Bodhi", "Cobalt", "Delta", "Ember", "Fjord", "Gala", "Helix", "Indus", "Juno",
             "Kaveri", "Lumen", "Meru", "Nimbus", "Orbit", "Prism", "Quanta", "Rudra", "Sutra", "Tara",
             "Umbra", "Vega", "Wick", "Xenon", "Yama", "Zephyr")
NAME_TAIL = ("Labs", "Works", "Systems", "Networks", "Technologies", "Ventures", "Digital", "Analytics")

# Fixed-severity demo companies for the dashboard picker: (name, sector, severity).
# Each has its own RNG stream (seed + 1000 + position), so severities were tuned per position to
# give two companies in each priority band (GREEN, YELLOW, ORANGE, RED) under the default seed.
# If you change the seed or the training data, re-check the spread with the tests.
SAMPLE_ARCHETYPES = (
    ("Steady Grower Ltd", "SaaS", 0.06),
    ("Early Warning Inc", "Logistics", 0.40),
    ("Quiet Recovery Co", "Fintech", 0.30),
    ("Hiring Freeze Labs", "EdTech", 0.50),
    ("Slow Bleed Systems", "Retail Tech", 0.65),
    ("Client Exodus Ltd", "D2C", 0.45),
    ("Runway Nearly Out Co", "Mobility", 0.65),
    ("Free Fall Ventures", "HealthTech", 0.90),
)

CSV_COLUMNS = ["company_id", "name", "sector", *SCALAR_SIGNALS, "collapsed"]


def _clip(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _count(rng: random.Random, level: float) -> int:
    """Poisson-like weekly count (slightly overdispersed), never negative."""
    return max(0, round(rng.gauss(level, 1.15 * math.sqrt(max(level, 1.0)))))


def _signals(rng: random.Random, s: float) -> dict[str, float]:
    g = rng.gauss
    return {
        "hiring_freeze_score": _clip(0.10 + 0.75 * s + g(0, 0.14)),
        "exec_departure_rate": _clip(0.04 + 0.50 * s + g(0, 0.10)),
        "news_negativity": _clip(0.15 + 0.65 * s + g(0, 0.16)),
        "review_sentiment": _clip(0.55 - 1.10 * s + g(0, 0.25), -1.0, 1.0),
        "engagement_signals": _clip(0.80 - 0.65 * s + g(0, 0.13)),
        "client_churn": _clip(0.03 + 0.40 * s + g(0, 0.09)),
        "delays": _clip(0.05 + 0.55 * s + g(0, 0.14)),
    }


def _postings(rng: random.Random, s: float, force_drop: bool | None = None) -> list[int]:
    base = rng.lognormvariate(3.6, 0.5)  # median ~36 postings/week
    trend = rng.uniform(-0.08, 0.08)  # gentle drift so no-drop series are not perfectly flat
    drops = rng.random() < 0.15 + 0.75 * s if force_drop is None else force_drop
    start = rng.randint(9, 19)
    ramp = rng.randint(1, 6)
    magnitude = _clip(0.25 + 0.60 * s + rng.gauss(0, 0.10), 0.10, 0.90)

    series = []
    for week in range(WEEKS):
        level = base * (1 + trend * week / (WEEKS - 1))
        if drops and week >= start:
            level *= 1 - magnitude * min(1.0, (week - start + 1) / ramp)
        series.append(_count(rng, level))
    return series


def make_company(rng: random.Random, severity: float, force_drop: bool | None = None) -> tuple[dict, list[int]]:
    return _signals(rng, severity), _postings(rng, severity, force_drop)


def _severity(rng: random.Random, collapsed: bool) -> float:
    return rng.betavariate(4.0, 2.2) if collapsed else rng.betavariate(1.8, 5.0)


def _name(rng: random.Random, taken: set[str]) -> str:
    while True:
        name = f"{rng.choice(NAME_HEAD)} {rng.choice(NAME_TAIL)}"
        if name not in taken:
            taken.add(name)
            return name
        # Head x tail has 208 combos; past that, disambiguate with a numeric suffix.
        if len(taken) >= len(NAME_HEAD) * len(NAME_TAIL):
            name = f"{name} {rng.randint(2, 999)}"
            if name not in taken:
                taken.add(name)
                return name


def generate(n: int, seed: int, out_dir: Path) -> dict:
    rng = random.Random(seed)
    out_dir.mkdir(parents=True, exist_ok=True)
    taken: set[str] = set()

    companies_path = out_dir / COMPANIES_CSV.name
    postings_path = out_dir / POSTINGS_CSV.name
    n_collapsed = 0
    with companies_path.open("w", newline="", encoding="utf-8") as cf, \
            postings_path.open("w", newline="", encoding="utf-8") as pf:
        cw = csv.DictWriter(cf, fieldnames=CSV_COLUMNS)
        cw.writeheader()
        pw = csv.writer(pf)
        pw.writerow(["company_id", "week", "postings"])
        for i in range(1, n + 1):
            cid = f"C{i:04d}"
            collapsed = rng.random() < COLLAPSE_RATE
            n_collapsed += collapsed
            signals, postings = make_company(rng, _severity(rng, collapsed))
            cw.writerow({
                "company_id": cid, "name": _name(rng, taken), "sector": rng.choice(SECTORS),
                **{k: f"{v:.4f}" for k, v in signals.items()}, "collapsed": int(collapsed),
            })
            pw.writerows((cid, w, p) for w, p in enumerate(postings, start=1))

    # One RNG stream per demo company: independent of --n and of each other, so retuning one
    # archetype's severity never changes the rest.
    samples = []
    for idx, (name, sector, severity) in enumerate(SAMPLE_ARCHETYPES):
        signals, postings = make_company(random.Random(seed + 1000 + idx), severity, force_drop=severity >= 0.45)
        samples.append({
            "name": name, "sector": sector,
            **{k: round(v, 4) for k, v in signals.items()},
            "weekly_job_postings": postings,
        })
    (out_dir / SAMPLES_JSON.name).write_text(json.dumps(samples, indent=2) + "\n", encoding="utf-8")

    return {"companies": n, "collapsed": n_collapsed, "weeks": WEEKS, "samples": len(samples), "out_dir": str(out_dir)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the synthetic CollapseCast dataset.")
    parser.add_argument("--n", type=int, default=600, help="number of companies (default 600)")
    parser.add_argument("--seed", type=int, default=42, help="random seed (default 42)")
    parser.add_argument("--out-dir", type=Path, default=COMPANIES_CSV.parent, help="output directory")
    args = parser.parse_args()
    summary = generate(args.n, args.seed, args.out_dir)
    print(
        f"Wrote {summary['companies']} companies ({summary['collapsed']} collapsed), "
        f"{summary['weeks']} weekly postings each, and {summary['samples']} sample companies "
        f"to {summary['out_dir']}"
    )


if __name__ == "__main__":
    main()
