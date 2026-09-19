# CollapseCast
AI-powered early warning system that predicts company collapse 3–6 months in advance using risk, demand, behavior, and failure signals.

CollapseCast takes a company's raw signals and runs them through a five-stage cascade. Each stage's output feeds the next, and the result is a priority band with recommended actions and an explanation of which signals caused what.

> **Demo data.** There is no real labeled history yet, so the models are trained on a synthetic dataset (regenerable, see below). Scores and metrics show that the cascade is wired correctly, not real-world accuracy.

## The cascade

| # | Stage | Method | Output |
|---|-------|--------|--------|
| 1 | **RISK** | Random Forest on hiring freeze, executive departures, news negativity. An Isolation Forest fallback covers a zero-label cold start. | `Risk_score` 0–1 |
| 2 | **DEMAND** | One-sided CUSUM change-point detection on weekly job postings | `Demand_score` (normalized drop) |
| 3 | **BEHAVIOR** | Random Forest on review sentiment, engagement and `Demand_score` | `Behavior_score` |
| 4 | **FAILURE** | XGBoost fusing the three scores with client churn and delays, then a sigmoid | `Failure_raw_score` |
| 5 | **RESOURCES** | No ML: sort and band. `>=0.80` RED, `0.50–0.79` ORANGE, `0.30–0.49` YELLOW, `<0.30` GREEN | Band + actions for Employees / Investors / HR |

Design notes:

- **No leakage between stages.** Stages 3 and 4 train on *out-of-fold* outputs of the stages before them, so they never learn from scores a model produced on its own training data.
- **Explanations add up.** Signal impacts are exact Shapley values through the whole cascade: a healthy baseline score plus the per-signal impacts equals the company's failure score.
- **Current stage** is the deepest of stages 1–4 whose score is at least 0.5 (`STAGE_ACTIVE_THRESHOLD` in `backend/app/config.py`), or 0 if none is active.
- **Isolation Forest fallback** (`COLLAPSECAST_RISK_MODE=isolation_forest`) flags *unusual* companies, not necessarily *distressed* ones, and only covers stage 1; stages 3 and 4 still need labels. The Random Forest also falls back on its own, with a warning, if the labels are unusable.

## Repository layout

```
backend/    FastAPI service, models, synthetic data, tests, Dockerfile
frontend/   React (Vite) dashboard
amplify.yml AWS Amplify Hosting build spec for the frontend
```

## Run locally

Prerequisites: Python 3.12, Node 20.19+ (24 LTS recommended).

**Backend** (http://localhost:8000, interactive docs at `/docs`):

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate   # on Debian/Ubuntu this needs the python3-venv package
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
```

Or with [uv](https://docs.astral.sh/uv/): `uv venv && uv pip install -r requirements-dev.txt`.

The models train on startup (about 10 seconds), and the server accepts requests once they are ready.

**Frontend** (http://localhost:5173):

```bash
cd frontend
npm ci
npm run dev
```

The frontend calls `http://localhost:8000` by default. To point it elsewhere, copy `.env.example` to `.env` and set `VITE_API_BASE_URL`. Append `?theme=light` or `?theme=dark` to the URL to force a theme.

**Tests** (backend): `cd backend && pytest`

## API

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/predict` | One company's raw signals in; current stage, all scores, band, recommended actions and the explainable breakdown out |
| `POST` | `/predict/batch` | Up to 100 companies, ranked by `Failure_raw_score` (stage 5 as a sort) |
| `GET` | `/samples` | Eight demo companies, healthiest first (not in the training set) |
| `GET` | `/model/info` | Training summary and band thresholds |
| `GET` | `/health` | Health check for App Runner |

Input signals for `/predict`: `hiring_freeze_score`, `exec_departure_rate`, `news_negativity`, `engagement_signals`, `client_churn`, `delays` (all 0–1), `review_sentiment` (−1 to 1), and `weekly_job_postings` (12–104 whole numbers, oldest first; the first 8 weeks are the baseline). An optional `name` is echoed back.

## Synthetic data

`backend/app/data/` holds a generated dataset (600 companies, 26 weeks of postings each) and 8 held-out demo companies. Regenerate it, deterministically, from `backend/`:

```bash
python -m app.data.generate_synthetic            # defaults: 600 companies, seed 42
python -m app.data.generate_synthetic --n 1000 --seed 7
```

The generator uses only the standard library. The demo companies' severities were tuned so the default seed shows all four bands; re-check the spread (`pytest`) after changing the seed.

## Configuration

| Variable | Where | Meaning |
|----------|-------|---------|
| `CORS_ORIGINS` | backend | Comma-separated allowed origins. Default `*`; set it to your Amplify URL in production. |
| `COLLAPSECAST_RISK_MODE` | backend | `random_forest` (default) or `isolation_forest` |
| `VITE_API_BASE_URL` | frontend, build time | Base URL of the API |

## Deployment (AWS)

Dependencies are pinned exactly: `backend/requirements.txt` is compiled from `backend/requirements.in` (whole tree, including transitive packages), and `frontend/package-lock.json` pins the frontend tree. XGBoost is the CPU-only `xgboost-cpu` build, which avoids about 290 MB of unused GPU libraries in the image.

**Backend on App Runner.** App Runner does not build Dockerfiles from a source repository, so build the image and push it to ECR:

```bash
cd backend
docker build -t collapsecast-api .
# tag and push to your ECR repository, then create an App Runner service from that image
```

Set the service port to `8000` and the HTTP health check path to `/health`. Startup trains the models (about 10 seconds), so use a generous health-check timeout and unhealthy threshold. Set `CORS_ORIGINS` to the frontend URL.

**Frontend on Amplify Hosting.** Connect this repository, mark it as a monorepo with app root `frontend` (the build spec is `amplify.yml`), and add the environment variable `VITE_API_BASE_URL` set to the App Runner service URL.

Verified locally: the API, the production frontend build, browser end-to-end tests (including phone widths down to 320 px), the Dockerfile with `hadolint`, and the image's runtime contents (production-only dependencies, read-only `app/`, served on port 8000). Not yet run: an actual `docker build` (no Docker daemon was available) and the AWS deployments themselves.
