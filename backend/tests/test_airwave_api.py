"""
Integration tests for AirWave Flask API routes.
Uses Flask test client — no real network calls for validation tests.
LLM/pipeline-dependent routes are skipped unless INTEGRATION=1 env var is set.
"""
import os
import json
import pytest
from unittest.mock import patch

# Allow running from backend/ root
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import create_app


@pytest.fixture()
def app():
    test_app = create_app()
    test_app.config.update({"TESTING": True})
    yield test_app


@pytest.fixture()
def client(app):
    return app.test_client()


# ── Health / metadata ─────────────────────────────────────────────────────────

class TestHealth:
    def test_root_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ok"

    def test_airwave_health_returns_ok(self, client):
        resp = client.get("/api/airwave/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ok"
        assert "data_sources" in data

    def test_triggers_returns_list(self, client):
        resp = client.get("/api/airwave/triggers")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert isinstance(data["data"], list)
        assert len(data["data"]) > 0

    def test_trigger_has_required_fields(self, client):
        resp = client.get("/api/airwave/triggers")
        for t in resp.get_json()["data"]:
            assert "id" in t
            assert "label" in t
            assert "icon" in t

    def test_agents_returns_list(self, client):
        resp = client.get("/api/airwave/agents")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert len(data["data"]) >= 4  # at least LCC, legacy, corporate, leisure


# ── Input validation (no network needed) ─────────────────────────────────────

class TestSimulateValidation:
    def _post(self, client, body):
        return client.post(
            "/api/airwave/simulate",
            data=json.dumps(body),
            content_type="application/json",
        )

    def test_missing_origin_returns_400(self, client):
        resp = self._post(client, {"destination": "JFK", "trigger_id": "FUEL_SPIKE"})
        assert resp.status_code == 400
        assert resp.get_json()["success"] is False

    def test_missing_destination_returns_400(self, client):
        resp = self._post(client, {"origin": "LHR", "trigger_id": "FUEL_SPIKE"})
        assert resp.status_code == 400

    def test_missing_trigger_returns_400(self, client):
        resp = self._post(client, {"origin": "LHR", "destination": "JFK"})
        assert resp.status_code == 400

    def test_invalid_iata_returns_400(self, client):
        resp = self._post(client, {"origin": "LONDONHEATHROW", "destination": "JFK", "trigger_id": "FUEL_SPIKE"})
        assert resp.status_code == 400
        assert "IATA" in resp.get_json()["error"]

    def test_same_origin_destination_returns_400(self, client):
        resp = self._post(client, {"origin": "LHR", "destination": "LHR", "trigger_id": "FUEL_SPIKE"})
        assert resp.status_code == 400

    def test_unknown_trigger_returns_400(self, client):
        resp = self._post(client, {"origin": "LHR", "destination": "JFK", "trigger_id": "MADE_UP_TRIGGER"})
        assert resp.status_code == 400

    def test_valid_trigger_ids_list_accepted(self, client):
        """Stacked shocks via trigger_ids list should pass validation (not return 400).
        Pipeline is mocked to prevent real network/LLM calls in CI."""
        with patch("app.api.airwave.build_live_seed_sync", side_effect=RuntimeError("mocked-no-network")):
            resp = self._post(client, {
                "origin": "LHR", "destination": "JFK",
                "trigger_ids": ["FUEL_SPIKE", "DISRUPTION_EVENT"],
            })
        # Validation passes (no 400). Pipeline throws 500, but not a validation error.
        assert resp.status_code != 400


# ── Rate limiter ──────────────────────────────────────────────────────────────

class TestRateLimiter:
    def _post(self, client, body=None):
        return client.post(
            "/api/airwave/simulate",
            data=json.dumps(body or {"origin": "LHR", "destination": "JFK", "trigger_id": "FUEL_SPIKE"}),
            content_type="application/json",
        )

    def test_rate_limit_triggers_after_max_calls(self, client):
        """After N+1 requests from the same IP within the window, expect 429."""
        from app.api.airwave import _rl_store, _RL_MAX_CALLS, _RL_WINDOW_SEC
        import time

        # Clear state for this IP
        test_ip = "127.0.0.1"
        _rl_store.pop(test_ip, None)

        # Mock the LLM + pipeline to return immediately (don't actually simulate)
        with patch("app.api.airwave.build_live_seed_sync", side_effect=RuntimeError("mocked")), \
             patch("app.api.airwave._get_client_ip", return_value=test_ip):
            responses = [self._post(client) for _ in range(_RL_MAX_CALLS + 1)]

        # First N calls: not 429 (may be 500 due to mocked pipeline, but not rate-limited)
        for i, resp in enumerate(responses[:-1]):
            assert resp.status_code != 429, f"Call {i+1} should not be rate-limited"

        # Last call: 429
        assert responses[-1].status_code == 429
        data = responses[-1].get_json()
        assert data["success"] is False
        assert "Rate limit" in data["error"]

    def test_rate_limit_response_has_retry_after_header(self, client):
        from app.api.airwave import _rl_store, _RL_MAX_CALLS
        test_ip = "10.0.0.99"
        _rl_store.pop(test_ip, None)

        with patch("app.api.airwave.build_live_seed_sync", side_effect=RuntimeError("mocked")), \
             patch("app.api.airwave._get_client_ip", return_value=test_ip):
            for _ in range(_RL_MAX_CALLS):
                self._post(client)
            resp = self._post(client)

        assert resp.status_code == 429
        assert "Retry-After" in resp.headers


# ── Cascade endpoint (no LLM) ─────────────────────────────────────────────────

class TestCascadeEndpoint:
    def _post(self, client, body):
        return client.post(
            "/api/airwave/cascade",
            data=json.dumps(body),
            content_type="application/json",
        )

    def test_cascade_fuel_spike(self, client):
        resp = self._post(client, {"trigger_id": "FUEL_SPIKE"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "impacts" in data["data"]
        assert len(data["data"]["impacts"]) > 0

    def test_cascade_stacked_triggers(self, client):
        resp = self._post(client, {"trigger_ids": ["FUEL_SPIKE", "DISRUPTION_EVENT"]})
        assert resp.status_code == 200

    def test_cascade_missing_trigger_returns_400(self, client):
        resp = self._post(client, {})
        assert resp.status_code == 400

    def test_cascade_node_has_plain_fields(self, client):
        resp = self._post(client, {"trigger_id": "FUEL_SPIKE"})
        for node in resp.get_json()["data"]["impacts"].values():
            assert "plain_label" in node
            assert "plain_icon" in node
