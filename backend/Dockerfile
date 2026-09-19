# CollapseCast API image for AWS App Runner.
# Build:  docker build -t collapsecast-api .        Run:  docker run -p 8000:8000 collapsecast-api

# ---- builder: resolve and install pinned runtime dependencies into a venv -------------------
FROM python:3.12-slim AS builder
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /build
COPY requirements.txt .
RUN python -m venv /opt/venv && /opt/venv/bin/pip install -r requirements.txt

# ---- runtime: slim base + the venv + app code only (no pip cache, no dev/test dependencies) --
FROM python:3.12-slim AS runtime
# No apt packages needed: the xgboost-cpu and scikit-learn wheels bundle their own OpenMP runtime
# (libgomp), so the slim base image is enough.
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
RUN useradd --create-home --uid 10001 appuser
WORKDIR /srv
COPY --from=builder /opt/venv /opt/venv
COPY app ./app
USER 10001

EXPOSE 8000
# App Runner health check: HTTP GET /health on port 8000 (configured in the service, not here).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
