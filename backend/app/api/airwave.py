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


# ── Helpers ───────────────────────────────────────────────────────────────────

def _disruption_to_dict(d) -> dict | None:
    """Serialise a DisruptionForecast (or None) to a JSON-safe dict."""
    if d is None:
        return None

    def _wx(w) -> dict:
        return {
            "airport_code": w.airport_code,
            "temperature_c": w.temperature_c,
            "weather_desc": w.weather_desc,
            "weather_emoji": w.weather_emoji,
            "wind_speed_kmh": w.wind_speed_kmh,
            "precipitation_prob": w.precipitation_prob,
            "visibility_km": w.visibility_km,
            "disruption_score": w.disruption_score,
            "risk_level": w.risk_level,
            "forecast_confidence": getattr(w, "forecast_confidence", "high"),
            "source": w.source,
        }

    return {
        "origin_weather": _wx(d.origin_weather),
        "dest_weather": _wx(d.dest_weather),
        "on_time_probability": d.on_time_probability,
        "delay_risk": d.delay_risk,
        "combined_score": d.combined_score,
        "primary_risk_factor": d.primary_risk_factor,
        "forecast_confidence": d.forecast_confidence,
    }


# ── Health / metadata ─────────────────────────────────────────────────────────

@airwave_bp.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "service": "AirWave Fare Intelligence Engine",
        "data_sources": {
            "serpapi": bool(Config.SERPAPI_KEY and not Config.SERPAPI_KEY.startswith("FILL_IN")),
            "travelpayouts": bool(Config.TRAVELPAYOUTS_KEY and not Config.TRAVELPAYOUTS_KEY.startswith("FILL_IN")),
            "opensky": True,
            "open_meteo": True,
            "macro": True,
        },
        "llm": bool(Config.LLM_API_KEY and not Config.LLM_API_KEY.startswith("FILL_IN")),
        "zep": bool(Config.ZEP_API_KEY and not Config.ZEP_API_KEY.startswith("FILL_IN")),
    })


@airwave_bp.route("/triggers", methods=["GET"])
def list_triggers():
    labels = {
        "FUEL_SPIKE": "Fuel Price Spike",
        "DEMAND_COLLAPSE": "Demand Collapse",
        "CAPACITY_DUMP": "Capacity Dump",
        "ROUTE_CANCELLATION": "Route Cancellation",
        "EXCHANGE_RATE": "Exchange Rate Shock",
        "DISRUPTION_EVENT": "Major Disruption Event",
    }
    triggers = [{"id": tid, "label": labels.get(tid, tid)} for tid in TRIGGER_SEEDS]
    return jsonify({"success": True, "data": triggers})


@airwave_bp.route("/agents", methods=["GET"])
def list_agents():
    return jsonify({
        "success": True,
        "data": [
            {
                "id": a.id, "name": a.name, "role": a.role,
                "hedge_ratio": a.hedge_ratio, "market_share": a.market_share,
            }
            for a in AIRLINE_AGENTS
        ],
    })


# ── Cascade only (fast, no LLM) ───────────────────────────────────────────────

@airwave_bp.route("/cascade", methods=["POST"])
def cascade():
    body = request.get_json() or {}
    trigger_id = body.get("trigger_id", "").upper()

    if trigger_id not in TRIGGER_SEEDS:
        return jsonify({
            "success": False,
            "error": f"Unknown trigger: {trigger_id}. Valid triggers: {list(TRIGGER_SEEDS.keys())}",
        }), 400

    impacts = run_cascade(trigger_id)
    return jsonify({
        "success": True,
        "data": {
            "trigger_id": trigger_id,
            "impacts": {
                k: {
                    "impact": v.impact, "confidence": v.confidence,
                    "days_to_effect": v.days_to_effect,
                    "mechanism": v.mechanism, "recovery": v.recovery,
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
        "departure_date": "2025-03-15",
        "return_date": "2025-03-22",
        "trip_type": "round_trip",
        "cabin_class": 1,
        "rounds": 8,
        "macro_override": { "vix": 28.5, "wti": 94.0 }
    }
    """
    body = request.get_json() or {}

    origin = (body.get("origin") or "").upper().strip()
    destination = (body.get("destination") or "").upper().strip()
    trigger_id = (body.get("trigger_id") or "").upper().strip()
    rounds = body.get("rounds")
    macro_override = body.get("macro_override")
    departure_date = body.get("departure_date") or None
    return_date = body.get("return_date") or None
    trip_type = body.get("trip_type") or "one_way"
    cabin_class = int(body.get("cabin_class") or 1)

    errors = []
    if not origin or len(origin) != 3:
        errors.append("origin must be a 3-letter IATA code")
    if not destination or len(destination) != 3:
        errors.append("destination must be a 3-letter IATA code")
    if trigger_id not in TRIGGER_SEEDS:
        errors.append(f"trigger_id must be one of: {list(TRIGGER_SEEDS.keys())}")
    if errors:
        return jsonify({"success": False, "error": "; ".join(errors)}), 400

    simulation_id = f"sim_{uuid.uuid4().hex[:8]}"
    logger.info(f"Starting simulation {simulation_id}: {origin}→{destination}, trigger={trigger_id}")

    try:
        seed = build_live_seed_sync(
            origin=origin, destination=destination, trigger_id=trigger_id,
            macro_override=macro_override, departure_date=departure_date,
            return_date=return_date, trip_type=trip_type, cabin_class=cabin_class,
        )

        if not Config.LLM_API_KEY or Config.LLM_API_KEY.startswith("FILL_IN"):
            return jsonify({
                "success": False,
                "error": "LLM_API_KEY not configured. Add your Gemini API key to .env",
            }), 503

        simulator = AirlineSimulator()
        result = simulator.run(seed=seed, simulation_id=simulation_id,
                               rounds=int(rounds) if rounds else None)

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
                        "round": a.round_num, "agent_id": a.agent_id,
                        "agent_name": a.agent_name, "decision": a.decision,
                        "magnitude_pct": round(a.magnitude * 100, 1),
                        "reasoning": a.reasoning, "confidence": a.confidence,
                    }
                    for a in result.actions
                ],
                "data_sources": result.sources,
                "created_at": result.created_at,
                "fare_details": {
                    "airline_name": seed.fare.airline_name,
                    "airline_logo": seed.fare.airline_logo,
                    "flight_number": seed.fare.flight_number,
                    "departure_time": seed.fare.departure_time,
                    "arrival_time": seed.fare.arrival_time,
                    "duration_min": seed.fare.duration_min,
                    "is_direct": seed.fare.is_direct,
                    "num_stops": seed.fare.num_stops,
                    "arrives_next_day": seed.fare.arrives_next_day,
                    "origin_airport_name": seed.fare.origin_airport_name,
                    "dest_airport_name": seed.fare.dest_airport_name,
                    "trip_type": seed.fare.trip_type,
                    "cabin_class": seed.fare.cabin_class,
                    "departure_date": seed.fare.departure_date,
                    "return_date": seed.fare.return_date,
                },
                "disruption": _disruption_to_dict(seed.disruption),
            },
        })

    except Exception as e:
        logger.error(f"Simulation failed: {traceback.format_exc()}")
        return jsonify({
            "success": False, "error": str(e), "simulation_id": simulation_id,
        }), 500


# ── Seed data only (no simulation) ───────────────────────────────────────────

@airwave_bp.route("/seed", methods=["POST"])
def seed_data():
    """
    Fetch live seed data for a route without running the simulation.
    Body: { "origin": "LHR", "destination": "JFK", "trigger_id": "FUEL_SPIKE",
            "departure_date": "2025-03-15", "return_date": null, "trip_type": "one_way",
            "cabin_class": 1 }
    """
    body = request.get_json() or {}
    origin = (body.get("origin") or "LHR").upper()
    destination = (body.get("destination") or "JFK").upper()
    trigger_id = (body.get("trigger_id") or "FUEL_SPIKE").upper()
    macro_override = body.get("macro_override")
    departure_date = body.get("departure_date") or None
    return_date = body.get("return_date") or None
    trip_type = body.get("trip_type") or "one_way"
    cabin_class = int(body.get("cabin_class") or 1)

    try:
        seed = build_live_seed_sync(
            origin=origin, destination=destination, trigger_id=trigger_id,
            macro_override=macro_override, departure_date=departure_date,
            return_date=return_date, trip_type=trip_type, cabin_class=cabin_class,
        )
        return jsonify({
            "success": True,
            "data": {
                "route": seed.route_label,
                "trigger_id": seed.trigger_id,
                "fare": {
                    "current_price_usd": seed.fare.current_price_usd,
                    "source": seed.fare.source,
                    "airline_name": seed.fare.airline_name,
                    "airline_logo": seed.fare.airline_logo,
                    "flight_number": seed.fare.flight_number,
                    "departure_time": seed.fare.departure_time,
                    "arrival_time": seed.fare.arrival_time,
                    "duration_min": seed.fare.duration_min,
                    "is_direct": seed.fare.is_direct,
                    "num_stops": seed.fare.num_stops,
                    "arrives_next_day": seed.fare.arrives_next_day,
                    "origin_airport_name": seed.fare.origin_airport_name,
                    "dest_airport_name": seed.fare.dest_airport_name,
                    "trip_type": seed.fare.trip_type,
                    "cabin_class": seed.fare.cabin_class,
                    "departure_date": seed.fare.departure_date,
                    "return_date": seed.fare.return_date,
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
                "disruption": _disruption_to_dict(seed.disruption),
            },
        })
    except Exception as e:
        logger.error(f"Seed fetch failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
