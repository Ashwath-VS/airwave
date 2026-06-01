"""
AirWave API Routes
/api/airwave/* — fare prediction simulation endpoints
"""

from __future__ import annotations

import traceback
import uuid
from flask import Blueprint, request, jsonify

from ..config import Config
from ..services.airline_simulator import AirlineSimulator, AIRLINE_AGENTS
from ..services.cascade_engine import run_cascade, TRIGGER_SEEDS
from ..services.data_pipeline import build_live_seed_sync
from ..utils.logger import get_logger

logger = get_logger("airwave.api")

airwave_bp = Blueprint("airwave", __name__)


# ── Health / metadata ─────────────────────────────────────────────────────────

@airwave_bp.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "service": "AirWave Fare Intelligence Engine",
        "data_sources": {
            "serpapi": bool(Config.SERPAPI_KEY and not Config.SERPAPI_KEY.startswith("FILL_IN")),
            "travelpayouts": bool(Config.TRAVELPAYOUTS_KEY and not Config.TRAVELPAYOUTS_KEY.startswith("FILL_IN")),
            "opensky": True,  # no key required
            "macro": True,
        },
        "llm": bool(Config.LLM_API_KEY and not Config.LLM_API_KEY.startswith("FILL_IN")),
        "zep": bool(Config.ZEP_API_KEY and not Config.ZEP_API_KEY.startswith("FILL_IN")),
    })


@airwave_bp.route("/triggers", methods=["GET"])
def list_triggers():
    """Return available macro shock triggers."""
    labels = {
        "FUEL_SPIKE": "Fuel Price Spike",
        "DEMAND_COLLAPSE": "Demand Collapse",
        "CAPACITY_DUMP": "Capacity Dump",
        "ROUTE_CANCELLATION": "Route Cancellation",
        "EXCHANGE_RATE": "Exchange Rate Shock",
        "DISRUPTION_EVENT": "Major Disruption Event",
    }
    triggers = [
        {"id": tid, "label": labels.get(tid, tid)}
        for tid in TRIGGER_SEEDS
    ]
    return jsonify({"success": True, "data": triggers})


@airwave_bp.route("/agents", methods=["GET"])
def list_agents():
    """Return the airline agent definitions."""
    return jsonify({
        "success": True,
        "data": [
            {
                "id": a.id,
                "name": a.name,
                "role": a.role,
                "hedge_ratio": a.hedge_ratio,
                "market_share": a.market_share,
            }
            for a in AIRLINE_AGENTS
        ],
    })


# ── Cascade only (fast, no LLM) ───────────────────────────────────────────────

@airwave_bp.route("/cascade", methods=["POST"])
def cascade():
    """
    Run BFS P&L cascade for a trigger. No LLM, instant.

    Body: { "trigger_id": "FUEL_SPIKE" }
    """
    body = request.get_json() or {}
    trigger_id = body.get("trigger_id", "").upper()

    if trigger_id not in TRIGGER_SEEDS:
        return jsonify({
            "success": False,
            "error": f"Unknown trigger: {trigger_id}. "
                     f"Valid triggers: {list(TRIGGER_SEEDS.keys())}",
        }), 400

    impacts = run_cascade(trigger_id)
    return jsonify({
        "success": True,
        "data": {
            "trigger_id": trigger_id,
            "impacts": {
                k: {
                    "impact": v.impact,
                    "confidence": v.confidence,
                    "days_to_effect": v.days_to_effect,
                    "mechanism": v.mechanism,
                    "recovery": v.recovery,
                }
                for k, v in impacts.items()
            },
        },
    })


# ── Full simulation ───────────────────────────────────────────────────────────

@airwave_bp.route("/simulate", methods=["POST"])
def simulate():
    """
    Run the full multi-agent fare prediction simulation.

    Body:
    {
        "origin": "LHR",
        "destination": "JFK",
        "trigger_id": "FUEL_SPIKE",
        "rounds": 8,               // optional, default from config
        "macro_override": {        // optional, pass real-time values from portfolio /api/market
            "vix": 28.5,
            "wti": 94.0,
            "sp500": -1.2,
            "usd_eur": 0.91,
            "usd_gbp": 0.78,
            "usd_jpy": 151.0
        }
    }
    """
    body = request.get_json() or {}

    origin = (body.get("origin") or "").upper().strip()
    destination = (body.get("destination") or "").upper().strip()
    trigger_id = (body.get("trigger_id") or "").upper().strip()
    rounds = body.get("rounds")
    macro_override = body.get("macro_override")

    # Validate
    errors = []
    if not origin or len(origin) != 3:
        errors.append("origin must be a 3-letter IATA code")
    if not destination or len(destination) != 3:
        errors.append("destination must be a 3-letter IATA code")
    if trigger_id not in TRIGGER_SEEDS:
        errors.append(
            f"trigger_id must be one of: {list(TRIGGER_SEEDS.keys())}"
        )
    if errors:
        return jsonify({"success": False, "error": "; ".join(errors)}), 400

    simulation_id = f"sim_{uuid.uuid4().hex[:8]}"
    logger.info(
        f"Starting simulation {simulation_id}: "
        f"{origin}→{destination}, trigger={trigger_id}"
    )

    try:
        # Step 1: fetch live seed data
        seed = build_live_seed_sync(
            origin=origin,
            destination=destination,
            trigger_id=trigger_id,
            macro_override=macro_override,
        )

        # Step 2: run agent simulation
        if not Config.LLM_API_KEY or Config.LLM_API_KEY.startswith("FILL_IN"):
            return jsonify({
                "success": False,
                "error": "LLM_API_KEY not configured. Add your Gemini API key to .env",
            }), 503

        simulator = AirlineSimulator()
        result = simulator.run(
            seed=seed,
            simulation_id=simulation_id,
            rounds=int(rounds) if rounds else None,
        )

        return jsonify({
            "success": True,
            "data": {
                "simulation_id": result.simulation_id,
                "route": result.route,
                "trigger_id": result.trigger_id,
                "seed_fare": result.seed_fare,
                "predicted_fare": result.predicted_fare,
                "fare_delta": result.fare_delta,
                "fare_delta_pct": round(result.fare_delta * 100, 1),
                "confidence": result.confidence,
                "days_to_effect": result.days_to_effect,
                "agent_consensus": result.agent_consensus,
                "narrative": result.narrative,
                "cascade_impacts": result.cascade_impacts,
                "agent_actions": [
                    {
                        "round": a.round_num,
                        "agent_id": a.agent_id,
                        "agent_name": a.agent_name,
                        "decision": a.decision,
                        "magnitude_pct": round(a.magnitude * 100, 1),
                        "reasoning": a.reasoning,
                        "confidence": a.confidence,
                    }
                    for a in result.actions
                ],
                "data_sources": result.sources,
                "created_at": result.created_at,
            },
        })

    except Exception as e:
        logger.error(f"Simulation failed: {traceback.format_exc()}")
        return jsonify({
            "success": False,
            "error": str(e),
            "simulation_id": simulation_id,
        }), 500


# ── Seed data only (no simulation) ───────────────────────────────────────────

@airwave_bp.route("/seed", methods=["POST"])
def seed_data():
    """
    Fetch live seed data for a route without running the simulation.
    Useful for the frontend to show current data before triggering a simulation.

    Body: { "origin": "LHR", "destination": "JFK", "trigger_id": "FUEL_SPIKE" }
    """
    body = request.get_json() or {}
    origin = (body.get("origin") or "LHR").upper()
    destination = (body.get("destination") or "JFK").upper()
    trigger_id = (body.get("trigger_id") or "FUEL_SPIKE").upper()
    macro_override = body.get("macro_override")

    try:
        seed = build_live_seed_sync(
            origin=origin,
            destination=destination,
            trigger_id=trigger_id,
            macro_override=macro_override,
        )
        return jsonify({
            "success": True,
            "data": {
                "route": seed.route_label,
                "trigger_id": seed.trigger_id,
                "fare": {
                    "current_price_usd": seed.fare.current_price_usd,
                    "source": seed.fare.source,
                },
                "demand": {
                    "flights_last_24h": seed.demand.flights_last_24h,
                    "demand_index": seed.demand.demand_index,
                    "source": seed.demand.source,
                },
                "history": {
                    "baseline_price_usd": seed.history.baseline_price_usd,
                    "month_avg": seed.history.month_avg,
                    "price_trend": seed.history.price_trend,
                    "source": seed.history.source,
                },
                "macro": {
                    "vix": seed.macro.vix,
                    "wti_price": seed.macro.wti_price,
                    "sp500_change": seed.macro.sp500_change,
                    "usd_eur": seed.macro.usd_eur,
                    "source": seed.macro.source,
                },
            },
        })
    except Exception as e:
        logger.error(f"Seed fetch failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
