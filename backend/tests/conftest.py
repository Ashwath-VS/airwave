"""
Shared pytest fixtures for AirWave test suite.
"""
import pytest


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Clear in-memory rate limiter state before every test to prevent bleed-between-tests."""
    from app.api.airwave import _rl_store
    _rl_store.clear()
    yield
    _rl_store.clear()
