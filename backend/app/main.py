"""CollapseCast API. Run locally with:  uvicorn app.main:app --reload --port 8000"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS
from app.pipeline.engine import CollapseCastEngine
from app.schemas import BatchRequest, BatchResponse, CompanySignals, PredictResponse, SampleCompany

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("collapsecast")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Train on startup and keep the models in memory. Uvicorn does not accept traffic until this
    # finishes, so App Runner's health check only passes once the models are ready.
    logger.info("Training CollapseCast cascade...")
    app.state.engine = CollapseCastEngine.train()
    logger.info("Ready.")
    yield


app = FastAPI(
    title="CollapseCast API",
    version="1.0.0",
    description="Predicts company collapse 3-6 months early with a 5-stage cascade: "
    "RISK -> DEMAND -> BEHAVIOR -> FAILURE -> RESOURCES.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _engine(request: Request) -> CollapseCastEngine:
    engine = getattr(request.app.state, "engine", None)
    if engine is None:
        raise HTTPException(status_code=503, detail="Models are still loading")
    return engine


@app.get("/health", tags=["ops"])
def health(request: Request) -> dict:
    """Liveness/readiness probe for AWS App Runner."""
    _engine(request)
    return {"status": "ok"}


@app.post("/predict", response_model=PredictResponse, tags=["predict"])
def predict(company: CompanySignals, request: Request) -> dict:
    """Run one company's raw signals through all five stages."""
    return _engine(request).analyze([company.model_dump()])[0]


@app.post("/predict/batch", response_model=BatchResponse, tags=["predict"])
def predict_batch(body: BatchRequest, request: Request) -> dict:
    """Stage 5 as a literal sort: score many companies and return them ranked by Failure_raw_score."""
    records = [c.model_dump() for c in body.companies]
    return {"results": _engine(request).analyze(records, rank=True)}


@app.get("/samples", response_model=list[SampleCompany], tags=["demo"])
def samples(request: Request) -> list[dict]:
    """Demo companies (not in the training set) for the dashboard's picker."""
    return _engine(request).samples


@app.get("/model/info", tags=["ops"])
def model_info(request: Request) -> dict:
    """Training summary. Metrics come from SYNTHETIC data and only show the pipeline is wired correctly."""
    return _engine(request).info()
