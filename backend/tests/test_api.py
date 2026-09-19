import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:  # entering the context runs the lifespan (trains the models)
        yield c


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_samples_can_be_posted_straight_back_to_predict(client):
    samples = client.get("/samples").json()
    assert len(samples) == 8
    response = client.post("/predict", json=samples[-1])  # includes the extra "sector" field
    assert response.status_code == 200
    body = response.json()
    assert body["band"] in ("RED", "ORANGE", "YELLOW", "GREEN")
    assert 0 <= body["scores"]["failure_raw"] <= 1
    assert body["breakdown"]["stages"][0]["contributions"]


def test_out_of_range_signal_is_rejected(client):
    bad = client.get("/samples").json()[0]
    bad["hiring_freeze_score"] = 1.7
    assert client.post("/predict", json=bad).status_code == 422


def test_too_short_postings_series_is_rejected(client):
    bad = client.get("/samples").json()[0]
    bad["weekly_job_postings"] = [10, 12, 9]
    assert client.post("/predict", json=bad).status_code == 422


def test_batch_endpoint_ranks_companies(client):
    samples = client.get("/samples").json()
    response = client.post("/predict/batch", json={"companies": samples})
    assert response.status_code == 200
    results = response.json()["results"]
    assert [r["priority_rank"] for r in results] == list(range(1, len(samples) + 1))
    assert results[0]["scores"]["failure_raw"] >= results[-1]["scores"]["failure_raw"]


def test_cors_header_is_present_for_browser_origins(client):
    response = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert "access-control-allow-origin" in response.headers


def test_model_info_reports_synthetic_data(client):
    assert client.get("/model/info").json()["metrics"]["data"] == "synthetic"
