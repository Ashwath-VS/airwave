"""
Unit tests for the AirWave cascade engine.
No network calls, no LLM — fully deterministic.
"""
import pytest
from app.services.cascade_engine import run_cascade, TRIGGER_SEEDS


class TestRunCascade:
    def test_fuel_spike_returns_impacts(self):
        impacts = run_cascade(["FUEL_SPIKE"])
        assert isinstance(impacts, dict)
        assert len(impacts) > 0

    def test_all_trigger_ids_run_without_error(self):
        for trigger_id in TRIGGER_SEEDS:
            impacts = run_cascade([trigger_id])
            assert impacts, f"Empty cascade for trigger {trigger_id}"

    def test_impact_nodes_have_required_fields(self):
        impacts = run_cascade(["FUEL_SPIKE"])
        for node_key, node in impacts.items():
            assert hasattr(node, "impact"),         f"{node_key} missing .impact"
            assert hasattr(node, "confidence"),     f"{node_key} missing .confidence"
            assert hasattr(node, "days_to_effect"), f"{node_key} missing .days_to_effect"
            assert hasattr(node, "mechanism"),      f"{node_key} missing .mechanism"

    def test_stacked_shocks_return_impacts(self):
        impacts = run_cascade(["FUEL_SPIKE", "DISRUPTION_EVENT"])
        assert isinstance(impacts, dict)
        assert len(impacts) > 0

    def test_demand_collapse_has_negative_or_zero_fare_impact(self):
        """Demand collapse should push fares down, not up."""
        impacts = run_cascade(["DEMAND_COLLAPSE"])
        fare_node = impacts.get("fare_level") or impacts.get("ticket_price") or impacts.get("average_fare")
        if fare_node is not None:
            assert fare_node.impact <= 0, (
                f"Demand collapse should reduce fares, got impact={fare_node.impact}"
            )

    def test_fuel_spike_increases_costs(self):
        """Fuel spike should propagate a positive cost impact."""
        impacts = run_cascade(["FUEL_SPIKE"])
        fuel_node = impacts.get("fuel_cost") or impacts.get("operating_cost")
        if fuel_node is not None:
            assert fuel_node.impact >= 0, (
                f"Fuel spike should raise costs, got impact={fuel_node.impact}"
            )

    def test_confidence_in_valid_range(self):
        impacts = run_cascade(["FUEL_SPIKE"])
        for node_key, node in impacts.items():
            assert 0.0 <= node.confidence <= 1.0, (
                f"{node_key} confidence {node.confidence} out of [0,1]"
            )

    def test_days_to_effect_non_negative(self):
        impacts = run_cascade(["EXCHANGE_RATE"])
        for node_key, node in impacts.items():
            assert node.days_to_effect >= 0, (
                f"{node_key} days_to_effect {node.days_to_effect} is negative"
            )
