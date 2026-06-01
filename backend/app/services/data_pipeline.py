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
                "type": "2",           # 1=round-trip (requires return_date), 2=one-way
                "currency": "USD",
                "hl": "en",
                "api_key": key,
            },
            timeout=15.0,
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
        flights = resp.json() or []

        # Total departures from origin airport = busyness proxy
        # OpenSky rarely populates estArrivalAirport for real-time data,
        # so we can't reliably filter to a specific destination.
        # Total departures normalised against a major-hub baseline (300/day = demand 1.0)
        total_departures = len(flights)

        # Attempt route-specific count from those that do have arrival data
        route_specific = [
            f for f in flights
            if (f.get("estArrivalAirport") or "").upper() == dest_icao.upper()
        ]
        route_count = len(route_specific)

        # Use route count if available, fall back to airport-wide proxy
        if route_count > 0:
            demand_idx = min(1.0, route_count / 12.0)  # 12+ direct flights = high
            flights_reported = route_count
        elif total_departures > 0:
            # Major hub: 300 departures/day; scale demand_index from total busyness
            demand_idx = min(1.0, total_departures / 300.0)
            # Estimate route-specific flights: assume destination captures ~3% of hub traffic
            flights_reported = max(1, int(total_departures * 0.03))
        else:
            return _synthetic_demand(origin, destination)

        return DemandData(
            origin_icao=origin_icao,
            destination_icao=dest_icao,
            flights_last_24h=flights_reported,
            avg_daily_flights=float(flights_reported),
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


# ── Macro data — Yahoo Finance + open.exchangerate-api ────────────────────────

FX_URL = "https://open.exchangerate-api.com/v6/latest/USD"
# Yahoo Finance v8 chart endpoint — works without auth (v7 bulk endpoint blocks scraping)
_YAHOO_V8 = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d"
_YAHOO_SYMBOLS = {"^VIX": "vix", "CL=F": "wti", "^GSPC": "sp500"}


async def _fetch_yahoo_v8(symbol: str, client: httpx.AsyncClient) -> float | None:
    """Fetch the latest market price for a single Yahoo Finance symbol."""
    import urllib.parse
    url = _YAHOO_V8.format(symbol=urllib.parse.quote(symbol, safe=""))
    try:
        resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8.0)
        resp.raise_for_status()
        meta = resp.json().get("chart", {}).get("result", [{}])[0].get("meta", {})
        price = meta.get("regularMarketPrice") or meta.get("previousClose")
        return float(price) if price is not None else None
    except Exception:
        return None


async def fetch_macro(client: httpx.AsyncClient) -> MacroData:
    """
    Fetches live macro data.
    Market data: Yahoo Finance v8 chart (no auth needed, per-symbol calls).
    FX rates: open.exchangerate-api (no key needed).
    Falls back to synthetic defaults where any fetch fails.
    """
    vix = wti = sp500_price = usd_eur = usd_gbp = usd_jpy = None

    # Parallel fetch for all Yahoo symbols + FX
    import asyncio as _asyncio

    vix_task = _fetch_yahoo_v8("^VIX", client)
    wti_task = _fetch_yahoo_v8("CL=F", client)
    sp500_task = _fetch_yahoo_v8("^GSPC", client)
    fx_resp_task = client.get(FX_URL, timeout=6.0)

    vix, wti, sp500_price, fx_resp = await _asyncio.gather(
        vix_task, wti_task, sp500_task, fx_resp_task, return_exceptions=True
    )

    # FX processing
    if isinstance(fx_resp, httpx.Response) and fx_resp.status_code == 200:
        fx = fx_resp.json().get("rates", {})
        usd_eur = float(fx.get("EUR", 0.92))
        usd_gbp = float(fx.get("GBP", 0.79))
        usd_jpy = float(fx.get("JPY", 149.5))

    # S&P 500: we need %change, not raw price — compute from meta if available
    sp500_change: float | None = None
    if sp500_price and isinstance(sp500_price, float) and sp500_price > 0:
        # Approximate: treat as fractional change placeholder; full change needs prev_close
        sp500_change = 0.0  # directionally neutral until we can get prev close

    # Suppress exception sentinels from gather
    vix = vix if isinstance(vix, float) else None
    wti = wti if isinstance(wti, float) else None

    synth = _synthetic_macro()
    has_live_market = any(v is not None for v in (vix, wti))
    has_live_fx = usd_eur is not None

    return MacroData(
        vix=vix if vix is not None else synth.vix,
        wti_price=wti if wti is not None else synth.wti_price,
        sp500_change=sp500_change if sp500_change is not None else synth.sp500_change,
        usd_eur=usd_eur if usd_eur is not None else synth.usd_eur,
        usd_gbp=usd_gbp if usd_gbp is not None else synth.usd_gbp,
        usd_jpy=usd_jpy if usd_jpy is not None else synth.usd_jpy,
        source=(
            "live" if (has_live_market and has_live_fx)
            else "partial" if (has_live_market or has_live_fx)
            else "synthetic"
        ),
    )


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
