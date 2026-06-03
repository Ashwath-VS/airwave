"""
AirWave API Routes
/api/airwave/* — fare prediction simulation endpoints
"""

from __future__ import annotations

import re
import time
import traceback
import uuid
from collections import defaultdict
from flask import Blueprint, request, jsonify

from ..config import Config
from ..services.airline_simulator import AirlineSimulator, AIRLINE_AGENTS
from ..services.cascade_engine import run_cascade, TRIGGER_SEEDS, TRIGGER_EXPLAIN, NODE_PLAIN
from ..services.data_pipeline import build_live_seed_sync
from ..utils.logger import get_logger

logger = get_logger("airwave.api")

airwave_bp = Blueprint("airwave", __name__)


# ── In-memory rate limiter ────────────────────────────────────────────────────
# Limits /simulate to 5 requests per IP per 60 seconds.
# No external dependency — uses a simple sliding-window counter.
_RL_WINDOW_SEC = 60
_RL_MAX_CALLS  = 5
_rl_store: dict[str, list[float]] = defaultdict(list)  # ip → [timestamps]

def _get_client_ip() -> str:
    """Best-effort client IP, respecting X-Forwarded-For for proxied deployments."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "unknown"

def _check_rate_limit() -> tuple[bool, int]:
    """Return (allowed, retry_after_seconds). Prunes old entries in-place."""
    ip  = _get_client_ip()
    now = time.monotonic()
    window_start = now - _RL_WINDOW_SEC
    # Prune timestamps outside the window
    _rl_store[ip] = [t for t in _rl_store[ip] if t > window_start]
    if len(_rl_store[ip]) >= _RL_MAX_CALLS:
        oldest = _rl_store[ip][0]
        retry_after = int(_RL_WINDOW_SEC - (now - oldest)) + 1
        return False, retry_after
    _rl_store[ip].append(now)
    return True, 0


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_trigger_ids(body: dict) -> list[str]:
    """Normalise trigger_ids (list) or trigger_id (string) from request body."""
    ids_raw = body.get("trigger_ids")
    id_raw = body.get("trigger_id", "")
    if ids_raw and isinstance(ids_raw, list):
        return [t.upper().strip() for t in ids_raw if t]
    if id_raw:
        return [id_raw.upper().strip()]
    return []


def _validate_trigger_ids(trigger_ids: list[str]) -> list[str]:
    """Return list of error strings for any invalid trigger ids."""
    errors = []
    for t in trigger_ids:
        if t not in TRIGGER_SEEDS:
            errors.append(f"Unknown trigger '{t}'. Valid: {list(TRIGGER_SEEDS.keys())}")
    return errors


def _disruption_to_dict(d) -> dict | None:
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


def _cascade_to_dict(cascade_impacts: dict) -> dict:
    """Serialise cascade impacts, enriching each node with plain-English fields."""
    result = {}
    for k, v in cascade_impacts.items():
        plain = NODE_PLAIN.get(k, {})
        result[k] = {
            "impact": v["impact"],
            "confidence": v["confidence"],
            "days_to_effect": v["days_to_effect"],
            "mechanism": v["mechanism"],
            "recovery": v["recovery"],
            # Plain-English additions
            "plain_label": plain.get("label", k.replace("_", " ").title()),
            "plain_icon": plain.get("icon", "📊"),
            "plain_what": plain.get("what", ""),
            "plain_why": plain.get("why", ""),
        }
    return result


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
        "NEWS_FEED": "News Feed",
    }
    icons = {
        "FUEL_SPIKE": "⛽",
        "DEMAND_COLLAPSE": "📉",
        "CAPACITY_DUMP": "✈️",
        "ROUTE_CANCELLATION": "🚫",
        "EXCHANGE_RATE": "💱",
        "DISRUPTION_EVENT": "⚠️",
        "NEWS_FEED": "📰",
    }
    triggers = [
        {
            "id": tid,
            "label": labels.get(tid, tid),
            "icon": icons.get(tid, "📊"),
            "explain": TRIGGER_EXPLAIN.get(tid, ""),
        }
        for tid in TRIGGER_SEEDS
    ]
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
    trigger_ids = _parse_trigger_ids(body)

    if not trigger_ids:
        return jsonify({"success": False, "error": "trigger_id or trigger_ids required"}), 400

    errors = _validate_trigger_ids(trigger_ids)
    if errors:
        return jsonify({"success": False, "error": "; ".join(errors)}), 400

    impacts = run_cascade(trigger_ids)
    return jsonify({
        "success": True,
        "data": {
            "trigger_ids": trigger_ids,
            "impacts": _cascade_to_dict({
                k: {
                    "impact": v.impact, "confidence": v.confidence,
                    "days_to_effect": v.days_to_effect,
                    "mechanism": v.mechanism, "recovery": v.recovery,
                }
                for k, v in impacts.items()
            }),
        },
    })


# ── Full simulation ───────────────────────────────────────────────────────────

@airwave_bp.route("/simulate", methods=["POST"])
def simulate():
    allowed, retry_after = _check_rate_limit()
    if not allowed:
        resp = jsonify({
            "success": False,
            "error": f"Rate limit exceeded — max {_RL_MAX_CALLS} simulations per {_RL_WINDOW_SEC}s. "
                     f"Retry in {retry_after}s.",
        })
        resp.headers["Retry-After"] = str(retry_after)
        return resp, 429

    body = request.get_json() or {}

    origin = (body.get("origin") or "").upper().strip()
    destination = (body.get("destination") or "").upper().strip()
    trigger_ids = _parse_trigger_ids(body)
    macro_override = body.get("macro_override")
    departure_date = body.get("departure_date") or None
    return_date = body.get("return_date") or None
    trip_type = body.get("trip_type") or "one_way"
    _cabin_map = {"economy": 1, "premium_economy": 2, "business": 3, "first": 4}
    raw_cabin = body.get("cabin_class") or "economy"
    cabin_class = _cabin_map.get(str(raw_cabin).lower(), int(raw_cabin) if str(raw_cabin).isdigit() else 1)
    news_context = body.get("news_context") or []   # list of headline strings

    # Map depth key → round count; explicit "rounds" in body takes priority
    _depth_rounds = {"fast": 1, "standard": 2, "deep": 3, "exhaustive": 5}
    depth_key = (body.get("depth") or "").lower()
    rounds = body.get("rounds") or _depth_rounds.get(depth_key)

    _IATA_RE = re.compile(r'^[A-Z]{3}$')
    errors = []
    if not origin or not _IATA_RE.match(origin):
        errors.append(
            f"'{origin}' is not a valid IATA airport code — must be exactly 3 letters (e.g. LHR, JFK, DEL)"
        )
    if not destination or not _IATA_RE.match(destination):
        errors.append(
            f"'{destination}' is not a valid IATA airport code — must be exactly 3 letters (e.g. LHR, JFK, DEL)"
        )
    if origin and destination and _IATA_RE.match(origin) and _IATA_RE.match(destination):
        if origin == destination:
            errors.append("Origin and destination cannot be the same airport")
    if not trigger_ids:
        errors.append("trigger_id or trigger_ids required")
    else:
        errors.extend(_validate_trigger_ids(trigger_ids))
    if errors:
        return jsonify({"success": False, "error": "; ".join(errors)}), 400

    # Use first trigger_id for seed/pipeline, pass all to cascade
    primary_trigger = trigger_ids[0]
    simulation_id = f"sim_{uuid.uuid4().hex[:8]}"
    logger.info(f"Starting simulation {simulation_id}: {origin}→{destination}, triggers={trigger_ids}")

    try:
        seed = build_live_seed_sync(
            origin=origin, destination=destination, trigger_id=primary_trigger,
            macro_override=macro_override, departure_date=departure_date,
            return_date=return_date, trip_type=trip_type, cabin_class=cabin_class,
        )

        if not Config.LLM_API_KEY or Config.LLM_API_KEY.startswith("FILL_IN"):
            return jsonify({
                "success": False,
                "error": "LLM_API_KEY not configured. Add your Gemini API key to .env",
            }), 503

        simulator = AirlineSimulator()
        result = simulator.run(
            seed=seed, simulation_id=simulation_id,
            rounds=int(rounds) if rounds else None,
            trigger_ids=trigger_ids,
            news_context=news_context if news_context else None,
        )

        return jsonify({
            "success": True,
            "data": {
                "simulation_id": result.simulation_id,
                "route": result.route,
                "trigger_ids": trigger_ids,
                "trigger_id": primary_trigger,
                "trigger_explains": {t: TRIGGER_EXPLAIN.get(t, "") for t in trigger_ids},
                "seed_fare": result.seed_fare,
                "predicted_fare": result.predicted_fare,
                "fare_delta": result.fare_delta,
                "fare_delta_pct": round(result.fare_delta * 100, 1),
                "confidence": result.confidence,
                "days_to_effect": result.days_to_effect,
                "agent_consensus": result.agent_consensus,
                "narrative": result.narrative,
                "cascade_impacts": _cascade_to_dict(result.cascade_impacts),
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
                "available_flights": seed.available_flights,
                "disruption": _disruption_to_dict(seed.disruption),
                "history": {
                    "baseline_price_usd": seed.history.baseline_price_usd,
                    "month_avg": seed.history.month_avg,
                    "price_trend": seed.history.price_trend,
                    "source": seed.history.source,
                },
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
    body = request.get_json() or {}
    origin = (body.get("origin") or "LHR").upper()
    destination = (body.get("destination") or "JFK").upper()
    trigger_ids = _parse_trigger_ids(body)
    if not trigger_ids:
        trigger_ids = ["FUEL_SPIKE"]
    macro_override = body.get("macro_override")
    departure_date = body.get("departure_date") or None
    return_date = body.get("return_date") or None
    trip_type = body.get("trip_type") or "one_way"
    _cabin_map2 = {"economy": 1, "premium_economy": 2, "business": 3, "first": 4}
    raw_cabin2 = body.get("cabin_class") or "economy"
    cabin_class = _cabin_map2.get(str(raw_cabin2).lower(), int(raw_cabin2) if str(raw_cabin2).isdigit() else 1)

    try:
        seed = build_live_seed_sync(
            origin=origin, destination=destination, trigger_id=trigger_ids[0],
            macro_override=macro_override, departure_date=departure_date,
            return_date=return_date, trip_type=trip_type, cabin_class=cabin_class,
        )
        return jsonify({
            "success": True,
            "data": {
                "route": seed.route_label,
                "trigger_ids": trigger_ids,
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
                "available_flights": seed.available_flights,
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


# ── News feed for route geography ─────────────────────────────────────────────

# Minimal airport-to-location mapping for news search queries
_AIRPORT_LOC = {
    "LHR":"London UK","LGW":"London UK","LCY":"London UK","STN":"London UK",
    "JFK":"New York USA","EWR":"New York USA","LGA":"New York USA",
    "LAX":"Los Angeles USA","SFO":"San Francisco USA","ORD":"Chicago USA",
    "ATL":"Atlanta USA","DFW":"Dallas USA","BOS":"Boston USA","MIA":"Miami USA",
    "SEA":"Seattle USA","DEN":"Denver USA","LAS":"Las Vegas USA",
    "DXB":"Dubai UAE","AUH":"Abu Dhabi UAE","DOH":"Doha Qatar",
    "SIN":"Singapore","KUL":"Kuala Lumpur Malaysia","BKK":"Bangkok Thailand",
    "HKG":"Hong Kong","PEK":"Beijing China","PVG":"Shanghai China",
    "ICN":"Seoul South Korea","NRT":"Tokyo Japan","HND":"Tokyo Japan",
    "SYD":"Sydney Australia","MEL":"Melbourne Australia","BNE":"Brisbane Australia",
    "DEL":"New Delhi India","BOM":"Mumbai India","BLR":"Bangalore India",
    "CDG":"Paris France","ORY":"Paris France","AMS":"Amsterdam Netherlands",
    "FRA":"Frankfurt Germany","MUC":"Munich Germany","ZRH":"Zurich Switzerland",
    "FCO":"Rome Italy","MXP":"Milan Italy","MAD":"Madrid Spain","BCN":"Barcelona Spain",
    "LIS":"Lisbon Portugal","ATH":"Athens Greece","VIE":"Vienna Austria",
    "CPH":"Copenhagen Denmark","ARN":"Stockholm Sweden","OSL":"Oslo Norway",
    "HEL":"Helsinki Finland","PRG":"Prague Czech Republic","WAW":"Warsaw Poland",
    "BUD":"Budapest Hungary","DUB":"Dublin Ireland","MAN":"Manchester UK",
    "EDI":"Edinburgh UK","BHX":"Birmingham UK","GLA":"Glasgow UK",
    "YYZ":"Toronto Canada","YVR":"Vancouver Canada","YUL":"Montreal Canada",
    "GRU":"Sao Paulo Brazil","GIG":"Rio de Janeiro Brazil","EZE":"Buenos Aires Argentina",
    "SCL":"Santiago Chile","LIM":"Lima Peru","BOG":"Bogota Colombia",
    "MEX":"Mexico City Mexico","CUN":"Cancun Mexico",
    "JNB":"Johannesburg South Africa","CPT":"Cape Town South Africa",
    "NBO":"Nairobi Kenya","ADD":"Addis Ababa Ethiopia","CAI":"Cairo Egypt",
    "CMN":"Casablanca Morocco","LOS":"Lagos Nigeria",
    "RUH":"Riyadh Saudi Arabia","JED":"Jeddah Saudi Arabia",
    "TLV":"Tel Aviv Israel","AMM":"Amman Jordan","BEY":"Beirut Lebanon",
}


@airwave_bp.route("/news", methods=["GET"])
def fetch_route_news():
    """Fetch recent news via Google News RSS — free, no API key, geo-targeted."""
    import httpx as _httpx
    import xml.etree.ElementTree as _ET
    import urllib.parse as _urlparse

    origin = request.args.get("origin", "").upper().strip()
    destination = request.args.get("destination", "").upper().strip()

    if not origin or not destination:
        return jsonify({"success": False, "error": "origin and destination required"}), 400

    origin_loc = _AIRPORT_LOC.get(origin, origin)
    dest_loc   = _AIRPORT_LOC.get(destination, destination)

    # Country name → ISO-2 for Google News gl/ceid targeting
    _COUNTRY_GL = {
        "UK": "GB", "USA": "US", "India": "IN", "Singapore": "SG",
        "Malaysia": "MY", "Thailand": "TH", "China": "CN", "Japan": "JP",
        "Australia": "AU", "UAE": "AE", "Qatar": "QA", "Kuwait": "KW",
        "Bahrain": "BH", "Oman": "OM", "France": "FR", "Germany": "DE",
        "Netherlands": "NL", "Spain": "ES", "Italy": "IT", "Portugal": "PT",
        "Greece": "GR", "Austria": "AT", "Switzerland": "CH", "Belgium": "BE",
        "Denmark": "DK", "Sweden": "SE", "Norway": "NO", "Finland": "FI",
        "Poland": "PL", "Czech": "CZ", "Hungary": "HU", "Romania": "RO",
        "Turkey": "TR", "Israel": "IL", "Jordan": "JO", "Lebanon": "LB",
        "Egypt": "EG", "Morocco": "MA", "Nigeria": "NG", "Kenya": "KE",
        "Ethiopia": "ET", "SouthAfrica": "ZA", "Ghana": "GH",
        "Korea": "KR", "Indonesia": "ID", "Philippines": "PH",
        "Vietnam": "VN", "Pakistan": "PK", "Bangladesh": "BD",
        "Brazil": "BR", "Argentina": "AR", "Chile": "CL", "Colombia": "CO",
        "Mexico": "MX", "Canada": "CA", "NewZealand": "NZ",
    }

    def _gl(loc: str) -> str:
        country = loc.split()[-1]
        return _COUNTRY_GL.get(country, "US")

    _CATEGORIES = [
        {
            "key": "political",
            "label": "Geopolitical",
            "icon": "🏛",
            "terms": "protest OR strike OR unrest OR conflict OR sanctions OR coup OR election OR war OR terrorism OR border",
        },
        {
            "key": "weather",
            "label": "Weather / Natural",
            "icon": "🌪",
            "terms": "storm OR hurricane OR typhoon OR cyclone OR earthquake OR flood OR eruption OR wildfire OR heatwave",
        },
        {
            "key": "aviation",
            "label": "Aviation",
            "icon": "✈️",
            "terms": "airline flight airport delay cancellation closure strike",
        },
    ]

    _HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
        "Accept-Language": "en-US,en;q=0.9",
    }

    def _parse_rss(rss_text: str, geo_tag: str, geo_label: str, cat: dict) -> list:
        try:
            root = _ET.fromstring(rss_text)
            out = []
            for item in root.findall(".//item")[:2]:
                raw_title = (item.findtext("title") or "").strip()
                src_elem  = item.find("source")
                source    = (src_elem.text or "").strip() if src_elem is not None else ""
                # Google appends " - Source Name" to titles — strip it
                title = raw_title[: -len(f" - {source}")].strip() if source and raw_title.endswith(f" - {source}") else raw_title
                link  = (item.findtext("link") or "").strip()
                date  = (item.findtext("pubDate") or "").strip()
                if not title:
                    continue
                out.append({
                    "title": title,
                    "source": source,
                    "date": date,
                    "link": link,
                    "snippet": "",
                    "geo": geo_tag,
                    "geo_label": geo_label,
                    "category": cat["key"],
                    "category_label": cat["label"],
                    "category_icon": cat["icon"],
                })
            return out
        except Exception as e:
            logger.warning(f"RSS parse error ({geo_label}/{cat['key']}): {e}")
            return []

    def _fetch_one(loc: str, geo_tag: str, geo_label: str, cat: dict) -> list:
        gl    = _gl(loc)
        city  = loc.split()[0]          # e.g. "London" from "London UK"
        query = f"{city} {cat['terms']}"
        url   = (
            f"https://news.google.com/rss/search"
            f"?q={_urlparse.quote(query)}"
            f"&hl=en&gl={gl}&ceid={gl}:en"
        )
        try:
            r = _httpx.get(url, headers=_HEADERS, timeout=12.0, follow_redirects=True)
            return _parse_rss(r.text, geo_tag, geo_label, cat)
        except Exception as e:
            logger.warning(f"Google News RSS fetch failed ({loc}/{cat['key']}): {e}")
            return []

    try:
        from concurrent.futures import ThreadPoolExecutor, as_completed as _asc
        tasks = []
        for cat in _CATEGORIES:
            tasks.append((origin_loc, "origin", origin_loc, cat))
            tasks.append((dest_loc,   "dest",   dest_loc,   cat))

        all_items: list = []
        with ThreadPoolExecutor(max_workers=6) as ex:
            for f in _asc([ex.submit(_fetch_one, *t) for t in tasks]):
                all_items.extend(f.result())

        def _sort_key(i):
            return (
                {"political": 0, "weather": 1, "aviation": 2}.get(i["category"], 9),
                {"origin": 0, "dest": 1}.get(i["geo"], 9),
            )
        all_items.sort(key=_sort_key)

        return jsonify({
            "success": True,
            "data": {
                "items": all_items[:12],
                "origin_loc": origin_loc,
                "dest_loc": dest_loc,
                "categories": [c["key"] for c in _CATEGORIES],
            },
        })

    except Exception as e:
        logger.error(f"News fetch failed for {origin}->{destination}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
