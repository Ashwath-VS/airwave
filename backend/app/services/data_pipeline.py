"""
AirWave Data Pipeline
Fetches live market data from SerpApi, OpenSky, Travelpayouts, and macro sources.
All functions gracefully degrade to synthetic baseline when API keys are absent.
"""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass, field
from typing import Optional

import httpx

from ..config import Config
from ..utils.logger import get_logger

logger = get_logger("airwave.data_pipeline")

# ── ICAO → IATA mapping (major airports) ─────────────────────────────────────

ICAO_TO_IATA: dict[str, str] = {
    "EGLL": "LHR", "EGKK": "LGW", "EGGW": "LTN", "EGSS": "STN",
    "KJFK": "JFK", "KLAX": "LAX", "KORD": "ORD", "KATL": "ATL",
    "KDFW": "DFW", "KSFO": "SFO", "KBOS": "BOS", "KIAD": "IAD",
    "KSEA": "SEA", "KMIA": "MIA", "KEWR": "EWR", "KDCA": "DCA",
    "EDDF": "FRA", "EDDM": "MUC", "EDDB": "BER", "EDDH": "HAM",
    "LFPG": "CDG", "LFPO": "ORY", "LSGG": "GVA", "LSZH": "ZRH",
    "EHAM": "AMS", "EBCI": "CRL", "EBBR": "BRU",
    "LIRF": "FCO", "LIMC": "MXP", "LEMD": "MAD", "LEBL": "BCN",
    "LPPT": "LIS", "LGAV": "ATH",
    "OMDB": "DXB", "OMSJ": "SHJ", "OMAA": "AUH",
    "VHHH": "HKG", "WSSS": "SIN", "RJTT": "HND", "RJAA": "NRT",
    "RKSI": "ICN", "ZBAA": "PEK", "ZSPD": "PVG", "VABB": "BOM",
    "VIDP": "DEL", "YSSY": "SYD", "YMML": "MEL",
    "CYYZ": "YYZ", "CYVR": "YVR", "CYUL": "YUL",
    "SAEZ": "EZE", "SBGR": "GRU", "SKBO": "BOG",
    "FAOR": "JNB", "HECA": "CAI", "DNMM": "LOS",
}

IATA_TO_ICAO: dict[str, str] = {v: k for k, v in ICAO_TO_IATA.items()}


def iata_to_icao(iata: str) -> str:
    return IATA_TO_ICAO.get(iata.upper(), f"K{iata.upper()}")


def icao_to_iata(icao: str) -> str:
    return ICAO_TO_IATA.get(icao.upper(), icao[1:] if icao.startswith("K") else icao)


# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class FareData:
    origin: str
    destination: str
    current_price_usd: float
    currency: str = "USD"
    source: str = "synthetic"
    departure_date: Optional[str] = None


@dataclass
class DemandData:
    origin_icao: str
    destination_icao: str
    flights_last_24h: int
    avg_daily_flights: float
    demand_index: float   # 0–1, 1 = very high demand
    source: str = "synthetic"


@dataclass
class HistoricalFare:
    origin: str
    destination: str
    baseline_price_usd: float
    month_avg: float
    price_trend: float   # +ve = prices rising
    source: str = "synthetic"


@dataclass
class MacroData:
    vix: float
    wti_price: float
    sp500_change: float
    usd_eur: float
    usd_gbp: float
    usd_jpy: float
    source: str = "synthetic"


@dataclass
class LiveSeed:
    """Unified seed object passed to the AirlineSimulator."""
    fare: FareData
    demand: DemandData
    history: HistoricalFare
    macro: MacroData
    trigger_id: str
    route_label: str = ""


# ── Synthetic fallbacks (used when API keys absent) ───────────────────────────

def _synthetic_fare(origin: str, destination: str) -> FareData:
    """Deterministic synthetic fare based on route hash."""
    base = 350 + (hash(f"{origin}{destination}") % 400)
    return FareData(
        origin=origin,
        destination=destination,
        current_price_usd=float(base),
        source="synthetic",
    )


def _synthetic_demand(origin: str, destination: str) -> DemandData:
    idx = 0.4 + (hash(f"demand{origin}{destination}") % 50) / 100
    return DemandData(
        origin_icao=iata_to_icao(origin),
        destination_icao=iata_to_icao(destination),
        flights_last_24h=int(6 + (hash(origin) % 12)),
        avg_daily_flights=float(8 + (hash(destination) % 6)),
        demand_index=round(idx, 2),
        source="synthetic",
    )


def _synthetic_history(origin: str, destination: str) -> HistoricalFare:
    base = 320 + (hash(f"hist{origin}{destination}") % 350)
    return HistoricalFare(
        origin=origin,
        destination=destination,
        baseline_price_usd=float(base),
        month_avg=float(base + 20),
        price_trend=0.05,
        source="synthetic",
    )


def _synthetic_macro() -> MacroData:
    return MacroData(
        vix=18.5, wti_price=82.0, sp500_change=0.4,
        usd_eur=0.92, usd_gbp=0.79, usd_jpy=149.5,
        source="synthetic",
    )


# ── SerpApi — live Google Flights fares ───────────────────────────────────────

async def fetch_live_fare(
    origin: str,
    destination: str,
    client: httpx.AsyncClient,
) -> FareData:
    key = Config.SERPAPI_KEY
    if not key or key.startswith("FILL_IN"):
        logger.debug("SERPAPI_KEY not set — using synthetic fare")
        return _synthetic_fare(origin, destination)

    try:
        resp = await client.get(
            "https://serpapi.com/search",
            params={
                "engine": "google_flights",
                "departure_id": origin,
                "arrival_id": destination,
                "outbound_date": _next_friday(),
                "currency": "USD",
                "hl": "en",
                "api_key": key,
            },
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()

        best_flights = data.get("best_flights", []) or data.get("other_flights", [])
        if best_flights:
            price = best_flights[0].get("price", 0)
            if price > 0:
                return FareData(
                    origin=origin,
                    destination=destination,
                    current_price_usd=float(price),
                    source="serpapi",
                )
    except Exception as e:
        logger.warning(f"SerpApi fetch failed ({origin}→{destination}): {e}")

    return _synthetic_fare(origin, destination)


# ── OpenSky — route demand proxy ─────────────────────────────────────────────

async def fetch_route_demand(
    origin: str,
    destination: str,
    client: httpx.AsyncClient,
) -> DemandData:
    origin_icao = iata_to_icao(origin)
    dest_icao = iata_to_icao(destination)

    now = int(time.time())
    window_start = now - 86400  # 24h rolling window

    try:
        resp = await client.get(
            "https://opensky-network.org/api/flights/departure",
            params={
                "airport": origin_icao,
                "begin": window_start,
                "end": now,
            },
            timeout=15.0,
        )
        resp.raise_for_status()
        flights = resp.json()

        # Filter flights going to destination ICAO
        matching = [
            f for f in flights
            if (f.get("estArrivalAirport") or "").upper() == dest_icao.upper()
        ]
        count = len(matching)
        avg = max(1, count)
        demand_idx = min(1.0, count / 20.0)

        return DemandData(
            origin_icao=origin_icao,
            destination_icao=dest_icao,
            flights_last_24h=count,
            avg_daily_flights=float(avg),
            demand_index=round(demand_idx, 2),
            source="opensky",
        )

    except Exception as e:
        logger.warning(f"OpenSky fetch failed ({origin_icao}→{dest_icao}): {e}")
        return _synthetic_demand(origin, destination)


# ── Travelpayouts — historical baseline ──────────────────────────────────────

async def fetch_fare_history(
    origin: str,
    destination: str,
    client: httpx.AsyncClient,
) -> HistoricalFare:
    key = Config.TRAVELPAYOUTS_KEY
    if not key or key.startswith("FILL_IN"):
        logger.debug("TRAVELPAYOUTS_KEY not set — using synthetic history")
        return _synthetic_history(origin, destination)

    try:
        resp = await client.get(
            "https://api.travelpayouts.com/v1/prices/cheap",
            params={
                "origin": origin,
                "destination": destination,
                "currency": "USD",
                "token": key,
            },
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()

        prices = data.get("data", {}).get(destination, {})
        if prices:
            values = [v.get("price", 0) for v in prices.values() if v.get("price")]
            if values:
                avg = sum(values) / len(values)
                latest = values[0]
                trend = (latest - avg) / avg if avg > 0 else 0.0
                return HistoricalFare(
                    origin=origin,
                    destination=destination,
                    baseline_price_usd=round(avg, 2),
                    month_avg=round(avg, 2),
                    price_trend=round(trend, 4),
                    source="travelpayouts",
                )
    except Exception as e:
        logger.warning(f"Travelpayouts fetch failed ({origin}→{destination}): {e}")

    return _synthetic_history(origin, destination)


# ── Macro data (reuse existing portfolio endpoint logic) ─────────────────────

async def fetch_macro(client: httpx.AsyncClient) -> MacroData:
    """
    Fetches macro data. In production this would call Yahoo Finance / exchangerate API.
    For now returns synthetic data that can be overridden by the caller passing real values.
    """
    return _synthetic_macro()


# ── Unified pipeline ─────────────────────────────────────────────────────────

async def build_live_seed(
    origin: str,
    destination: str,
    trigger_id: str,
    macro_override: Optional[dict] = None,
) -> LiveSeed:
    """
    Fetch all data sources concurrently and return a unified LiveSeed.
    Falls back gracefully when API keys are absent.
    """
    async with httpx.AsyncClient() as client:
        fare_task = fetch_live_fare(origin, destination, client)
        demand_task = fetch_route_demand(origin, destination, client)
        history_task = fetch_fare_history(origin, destination, client)
        macro_task = fetch_macro(client)

        fare, demand, history, macro = await asyncio.gather(
            fare_task, demand_task, history_task, macro_task
        )

    # Apply caller-supplied macro override (e.g., from portfolio /api/market)
    if macro_override:
        macro = MacroData(
            vix=macro_override.get("vix", macro.vix),
            wti_price=macro_override.get("wti", macro.wti_price),
            sp500_change=macro_override.get("sp500", macro.sp500_change),
            usd_eur=macro_override.get("usd_eur", macro.usd_eur),
            usd_gbp=macro_override.get("usd_gbp", macro.usd_gbp),
            usd_jpy=macro_override.get("usd_jpy", macro.usd_jpy),
            source="caller_supplied",
        )

    return LiveSeed(
        fare=fare,
        demand=demand,
        history=history,
        macro=macro,
        trigger_id=trigger_id,
        route_label=f"{origin} → {destination}",
    )


def build_live_seed_sync(
    origin: str,
    destination: str,
    trigger_id: str,
    macro_override: Optional[dict] = None,
) -> LiveSeed:
    """Synchronous wrapper for use inside Flask routes."""
    return asyncio.run(build_live_seed(origin, destination, trigger_id, macro_override))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _next_friday() -> str:
    """Return next Friday's date as YYYY-MM-DD."""
    import datetime
    today = datetime.date.today()
    days_ahead = (4 - today.weekday()) % 7 or 7
    return (today + datetime.timedelta(days=days_ahead)).isoformat()
