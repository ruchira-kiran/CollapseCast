import pytest

from app.pipeline.engine import CollapseCastEngine


@pytest.fixture(scope="session")
def engine() -> CollapseCastEngine:
    """One trained engine shared by all tests (training takes a few seconds)."""
    return CollapseCastEngine.train()
