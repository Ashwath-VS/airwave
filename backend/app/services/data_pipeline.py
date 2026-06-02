"""
AirWave Data Pipeline
Fetches live market data from SerpApi, OpenSky, Travelpayouts, Open-Meteo, and macro sources.
All functions gracefully degrade to synthetic baseline when API keys are absent.
"""

from __future__ import annotations

import asyncio
import datetime
import time
from dataclasses import dataclass
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


# Lat/long for major airports (Open-Meteo queries)
AIRPORT_COORDS: dict[str, tuple[float, float]] = {
    "LHR": (51.477, -0.461), "LGW": (51.157, -0.182), "STN": (51.885, 0.235),
    "JFK": (40.641, -73.779), "LAX": (33.943, -118.408), "ORD": (41.974, -87.908),
    "ATL": (33.637, -84.428), "DFW": (32.897, -97.038), "SFO": (37.619, -122.375),
    "BOS": (42.365, -71.010), "MIA": (25.796, -80.287), "EWR": (40.693, -74.168),
    "SEA": (47.449, -122.309), "IAD": (38.944, -77.456), "DCA": (38.852, -77.038),
    "FRA": (50.026, 8.543),   "MUC": (48.354, 11.786),  "BER": (52.366, 13.503),
    "CDG": (49.013, 2.550),   "ORY": (48.723, 2.380),   "AMS": (52.309, 4.764),
    "BRU": (50.902, 4.484),   "ZRH": (47.458, 8.548),   "GVA": (46.238, 6.109),
    "FCO": (41.804, 12.251),  "MXP": (45.630, 8.728),   "MAD": (40.494, -3.567),
    "BCN": (41.297, 2.083),   "LIS": (38.774, -9.135),  "ATH": (37.936, 23.944),
    "DXB": (25.253, 55.365),  "AUH": (24.433, 54.651),  "SHJ": (25.329, 55.518),
    "HKG": (22.309, 113.915), "SIN": (1.359, 103.989),  "HND": (35.549, 139.780),
    "NRT": (35.765, 140.386), "ICN": (37.460, 126.441), "PEK": (40.080, 116.584),
    "PVG": (31.152, 121.805), "BOM": (19.089, 72.868),  "DEL": (28.556, 77.100),
    "SYD": (-33.946, 151.177),"MEL": (-37.673, 144.843),
    "YYZ": (43.677, -79.631), "YVR": (49.195, -123.180),"YUL": (45.470, -73.741),
    "EZE": (-34.822, -58.535),"GRU": (-23.435, -46.473),
    "JNB": (-26.134, 28.242), "CAI": (30.122, 31.406),  "LOS": (6.577, 3.321),
}


# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class FareData:
    origin: str
    destination: str
    current_price_usd: float
    currency: str = "USD"
    source: str = "synthetic"
    departure_date: Optional[str] = None
    return_date: Optional[str] = None
    trip_type: str = "one_way"
    cabin_class: int = 1
    airline_name: str = ""
    airline_logo: str = ""
    flight_number: str = ""
    departure_time: str = ""
    arrival_time: str = ""
    duration_min: int = 0
    is_direct: bool = False
    arrives_next_day: bool = False
    origin_airport_name: str = ""
    dest_airport_name: str = ""
    num_stops: int = 0


@dataclass
class DemandData:
    origin_icao: str
    destination_icao: str
    flights_last_24h: int
    avg_daily_flights: float
    demand_index: float
    source: str = "synthetic"


@dataclass
class HistoricalFare:
    origin: str
    destination: str
    baseline_price_usd: float
    month_avg: float
    price_trend: float
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
class WeatherData:
    airport_code: str
    temperature_c: float
    weather_code: int
    weather_desc: str
    weather_emoji: str
    wind_speed_kmh: float
    precipitation_prob: int
    visibility_km: float
    disruption_score: int
    risk_level: str
    forecast_confidence: str = "high"
    source: str = "open-meteo"


@dataclass
class DisruptionForecast:
    origin_weather: WeatherData
    dest_weather: WeatherData
    on_time_probability: float
    delay_risk: str
    combined_score: int
    primary_risk_factor: str
    forecast_confidence: str
    source: str = "open-meteo"


@dataclass
class LiveSeed:
    """Unified seed object passed to the AirlineSimulator."""
    fare: FareData
    demand: DemandData
    history: HistoricalFare
    macro: MacroData
    trigger_id: str
    route_label: str = ""
    disruption: Optional[DisruptionForecast] = None


# ── Synthetic fallbacks ───────────────────────────────────────────────────────

def _synthetic_fare(origin: str, destination: str) -> FareData:
    base = 350 + (hash(f"{origin}{destination}") % 400)
    return FareData(origin=origin, destination=destination,
                    current_price_usd=float(base), source="synthetic")


def _synthetic_demand(origin: str, destination: str) -> DemandData:
    idx = 0.4 + (hash(f"demand{origin}{destination}") % 50) / 100
    return DemandData(
        origin_icao=iata_to_icao(origin), destination_icao=iata_to_icao(destination),
        flights_last_24h=int(6 + (hash(origin) % 12)),
        avg_daily_flights=float(8 + (hash(destination) % 6)),
        demand_index=round(idx, 2), source="synthetic",
    )


def _synthetic_history(origin: str, destination: str) -> HistoricalFare:
    base = 320 + (hash(f"hist{origin}{destination}") % 350)
    return HistoricalFare(origin=origin, destination=destination,
                          baseline_price_usd=float(base), month_avg=float(base + 20),
                          price_trend=0.05, source="synthetic")


def _synthetic_macro() -> MacroData:
    return MacroData(vix=18.5, wti_price=82.0, sp500_change=0.4,
                     usd_eur=0.92, usd_gbp=0.79, usd_jpy=149.5, source="synthetic")


def _neutral_weather(airport_code: str) -> WeatherData:
    return WeatherData(
        airport_code=airport_code, temperature_c=15.0, weather_code=0,
        weather_desc="Clear sky", weather_emoji="☀️", wind_speed_kmh=10.0,
        precipitation_prob=5, visibility_km=15.0, disruption_score=5,
        risk_level="low", forecast_confidence="low", source="synthetic",
    )


# ── Weather helpers ───────────────────────────────────────────────────────────

def _wmo_to_desc(code: int) -> tuple[str, str]:
    if code == 0:               return "Clear sky", "☀️"
    if code in (1, 2, 3):      return "Partly cloudy", "⛅"
    if code in (45, 48):        return "Fog", "🌫️"
    if code in (51, 53, 55):    return "Drizzle", "🌦️"
    if code in (61, 63, 65):    return "Rain", "🌧️"
    if code in (71, 73, 75, 77): return "Snow", "🌨️"
    if code in (80, 81, 82):    return "Rain showers", "🌩️"
    if code in (85, 86):        return "Snow showers", "❄️"
    if code in (95, 96, 99):    return "Thunderstorm", "⛈️"
    return "Overcast", "🌥️"


def _disruption_score(weather_code: int, wind_kmh: float,
                      precip_prob: int, visibility_km: float) -> tuple[int, str]:
    score = 0
    if weather_code in (95, 96, 99):             score += 40
    elif weather_code in (71, 73, 75, 77, 85, 86): score += 30
    elif weather_code in (65, 82):               score += 20
    elif weather_code in (45, 48):               score += 25
    elif weather_code in (61, 63, 80, 81):       score += 10

    if wind_kmh >= 80:    score += 30
    elif wind_kmh >= 55:  score += 20
    elif wind_kmh >= 35:  score += 10
    elif wind_kmh >= 20:  score += 5

    score += int(precip_prob * 0.15)

    if visibility_km < 0.5:   score += 20
    elif visibility_km < 2.0: score += 12
    elif visibility_km < 5.0: score += 5

    score = min(100, score)
    if score >= 60:   level = "severe"
    elif score >= 40: level = "high"
    elif score >= 20: level = "moderate"
    else:             level = "low"
    return score, level


def _parse_flight_time(raw: str) -> str:
    return raw[-5:] if raw and len(raw) >= 16 else ""


def _build_disruption(origin_wx: WeatherData, dest_wx: WeatherData) -> DisruptionForecast:
    combined_score = min(100, int(
        origin_wx.disruption_score * 0.45 + dest_wx.disruption_score * 0.45 + 5
    ))
    on_time_prob = max(0.30, 1.0 - (combined_score / 100.0) * 0.75)

    if combined_score >= 60:   delay_risk = "severe"
    elif combined_score >= 40: delay_risk = "high"
    elif combined_score >= 20: delay_risk = "moderate"
    else:                      delay_risk = "low"

    worst = (origin_wx if origin_wx.disruption_score >= dest_wx.disruption_score
             else dest_wx)
    if worst.wind_speed_kmh >= 55:
        primary = f"Strong winds {worst.wind_speed_kmh:.0f} km/h at {worst.airport_code}"
    elif worst.weather_code in (45, 48):
        primary = f"Fog, visibility {worst.visibility_km:.1f} km at {worst.airport_code}"
    elif worst.weather_code in (95, 96, 99):
        primary = f"Thunderstorm at {worst.airport_code}"
    elif worst.weather_code in (71, 73, 75, 77, 85, 86):
        primary = f"Snow at {worst.airport_code}"
    elif worst.disruption_score >= 20:
        primary = f"{worst.weather_desc} at {worst.airport_code}"
    else:
        primary = "No significant weather disruption"

    fc_conf = (origin_wx.forecast_confidence
               if origin_wx.disruption_score >= dest_wx.disruption_score
               else dest_wx.forecast_confidence)

    return DisruptionForecast(
        origin_weather=origin_wx, dest_weather=dest_wx,
        on_time_probability=round(on_time_prob, 2),
        delay_risk=delay_risk, combined_score=combined_score,
        primary_risk_factor=primary, forecast_confidence=fc_conf,
    )


# ── Open-Meteo — airport weather ─────────────────────────────────────────────

async def fetch_weather(
    airport_code: str,
    client: httpx.AsyncClient,
    forecast_date: Optional[str] = None,
) -> WeatherData:
    """Fetch weather for an airport via Open-Meteo (no API key required)."""
    coords = AIRPORT_COORDS.get(airport_code.upper())
    if not coords:
        return _neutral_weather(airport_code)

    lat, lon = coords
    today = datetime.date.today()

    if forecast_date:
        try:
            target = datetime.date.fromisoformat(forecast_date)
        except ValueError:
            target = today
    else:
        target = today

    days_ahead = (target - today).days
    fc_confidence = "high" if days_ahead <= 3 else ("medium" if days_ahead <= 7 else "low")

    try:
        if 0 < days_ahead <= 16:
            date_str = target.isoformat()
            resp = await client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat, "longitude": lon,
                    "daily": "weathercode,windspeed_10m_max,precipitation_probability_max",
                    "hourly": "visibility",
                    "start_date": date_str, "end_date": date_str,
                    "timezone": "UTC", "windspeed_unit": "kmh",
                },
                timeout=10.0,
            )
            resp.raise_for_status()
            d = resp.json()
            daily = d.get("daily", {})
            hourly = d.get("hourly", {})
            wcode = int((daily.get("weathercode") or [0])[0])
            wind = float((daily.get("windspeed_10m_max") or [0.0])[0])
            precip_prob = int((daily.get("precipitation_probability_max") or [0])[0])
            vis_vals = hourly.get("visibility") or []
            visibility_km = float(vis_vals[12]) / 1000.0 if len(vis_vals) > 12 else 10.0
            temperature_c = 15.0
        else:
            resp = await client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat, "longitude": lon,
                    "current_weather": "true",
                    "hourly": "precipitation_probability,visibility",
                    "forecast_days": 1, "timezone": "UTC", "windspeed_unit": "kmh",
                },
                timeout=10.0,
            )
            resp.raise_for_status()
            d = resp.json()
            cw = d.get("current_weather", {})
            wcode = int(cw.get("weathercode", 0))
            wind = float(cw.get("windspeed", 0.0))
            temperature_c = float(cw.get("temperature", 15.0))
            hourly = d.get("hourly", {})
            precip_list = hourly.get("precipitation_probability") or []
            precip_prob = int(precip_list[0]) if precip_list else 0
            vis_list = hourly.get("visibility") or []
            visibility_km = float(vis_list[0]) / 1000.0 if vis_list else 10.0

        desc, emoji = _wmo_to_desc(wcode)
        score, level = _disruption_score(wcode, wind, precip_prob, visibility_km)
        return WeatherData(
            airport_code=airport_code,
            temperature_c=round(temperature_c, 1),
            weather_code=wcode, weather_desc=desc, weather_emoji=emoji,
            wind_speed_kmh=round(wind, 1), precipitation_prob=precip_prob,
            visibility_km=round(visibility_km, 1),
            disruption_score=score, risk_level=level,
            forecast_confidence=fc_confidence, source="open-meteo",
        )
    except Exception as e:
        logger.warning(f"Open-Meteo fetch failed for {airport_code}: {e}")
        return _neutral_weather(airport_code)


# ── SerpApi — live Google Flights fares ───────────────────────────────────────

async def fetch_live_fare(
    origin: str,
    destination: str,
    client: httpx.AsyncClient,
    departure_date: Optional[str] = None,
    return_date: Optional[str] = None,
    trip_type: str = "one_way",
    cabin_class: int = 1,
) -> FareData:
    key = Config.SERPAPI_KEY
    if not key or key.startswith("FILL_IN"):
        fare = _synthetic_fare(origin, destination)
        fare.departure_date = departure_date or _next_friday()
        fare.trip_type = trip_type
        fare.cabin_class = cabin_class
        return fare

    outbound = departure_date or _next_friday()
    search_type = "1" if trip_type == "round_trip" and return_date else "2"

    params: dict = {
        "engine": "google_flights",
        "departure_id": origin, "arrival_id": destination,
        "outbound_date": outbound, "type": search_type,
        "travel_class": cabin_class, "currency": "USD", "hl": "en",
        "api_key": key,
    }
    if search_type == "1" and return_date:
        params["return_date"] = return_date

    try:
        resp = await client.get("https://serpapi.com/search", params=params, timeout=15.0)
        resp.raise_for_status()
        data = resp.json()
        best_flights = data.get("best_flights", []) or data.get("other_flights", [])
        if best_flights:
            best = best_flights[0]
            price = best.get("price", 0)
            if price > 0:
                flights_list = best.get("flights", [])
                first_leg = flights_list[0] if flights_list else {}
                last_leg = flights_list[-1] if flights_list else {}
                dep_airport = first_leg.get("departure_airport", {})
                arr_airport = last_leg.get("arrival_airport", {})
                dep_raw = dep_airport.get("time", "")
                arr_raw = arr_airport.get("time", "")
                num_stops = max(0, len(flights_list) - 1)
                dep_date = dep_raw[:10] if dep_raw else ""
                arr_date = arr_raw[:10] if arr_raw else ""
                return FareData(
                    origin=origin, destination=destination,
                    current_price_usd=float(price), source="serpapi",
                    departure_date=outbound, return_date=return_date,
                    trip_type=trip_type, cabin_class=cabin_class,
                    airline_name=first_leg.get("airline", ""),
                    airline_logo=first_leg.get("airline_logo", ""),
                    flight_number=first_leg.get("flight_number", ""),
                    departure_time=_parse_flight_time(dep_raw),
                    arrival_time=_parse_flight_time(arr_raw),
                    duration_min=int(best.get("total_duration") or 0),
                    is_direct=(num_stops == 0),
                    arrives_next_day=bool(dep_date and arr_date and dep_date != arr_date),
                    origin_airport_name=dep_airport.get("name", ""),
                    dest_airport_name=arr_airport.get("name", ""),
                    num_stops=num_stops,
                )
    except Exception as e:
        logger.warning(f"SerpApi fetch failed ({origin}→{destination}): {e}")

    fare = _synthetic_fare(origin, destination)
    fare.departure_date = outbound
    fare.return_date = return_date
    fare.trip_type = trip_type
    fare.cabin_class = cabin_class
    return fare


# ── OpenSky — route demand proxy ─────────────────────────────────────────────

async def fetch_route_demand(
    origin: str,
    destination: str,
    client: httpx.AsyncClient,
) -> DemandData:
    origin_icao = iata_to_icao(origin)
    dest_icao = iata_to_icao(destination)
    now = int(time.time())
    window_start = now - 86400

    try:
        resp = await client.get(
            "https://opensky-network.org/api/flights/departure",
            params={"airport": origin_icao, "begin": window_start, "end": now},
            timeout=15.0,
        )
        resp.raise_for_status()
        flights = resp.json() or []
        total_departures = len(flights)
        route_specific = [
            f for f in flights
            if (f.get("estArrivalAirport") or "").upper() == dest_icao.upper()
        ]
        route_count = len(route_specific)

        if route_count > 0:
            demand_idx = min(1.0, route_count / 12.0)
            flights_reported = route_count
        elif total_departures > 0:
            demand_idx = min(1.0, total_departures / 300.0)
            flights_reported = max(1, int(total_departures * 0.03))
        else:
            return _synthetic_demand(origin, destination)

        return DemandData(
            origin_icao=origin_icao, destination_icao=dest_icao,
            flights_last_24h=flights_reported, avg_daily_flights=float(flights_reported),
            demand_index=round(demand_idx, 2), source="opensky",
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
        return _synthetic_history(origin, destination)

    try:
        resp = await client.get(
            "https://api.travelpayouts.com/v1/prices/cheap",
            params={"origin": origin, "destination": destination,
                    "currency": "USD", "token": key},
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
                    origin=origin, destination=destination,
                    baseline_price_usd=round(avg, 2), month_avg=round(avg, 2),
                    price_trend=round(trend, 4), source="travelpayouts",
                )
    except Exception as e:
        logger.warning(f"Travelpayouts fetch failed ({origin}→{destination}): {e}")
    return _synthetic_history(origin, destination)


# ── Macro data — Yahoo Finance + open.exchangerate-api ────────────────────────

FX_URL = "https://open.exchangerate-api.com/v6/latest/USD"
_YAHOO_V8 = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d"


async def _fetch_yahoo_v8(symbol: str, client: httpx.AsyncClient) -> float | None:
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
    vix, wti, sp500_price, fx_resp = await asyncio.gather(
        _fetch_yahoo_v8("^VIX", client),
        _fetch_yahoo_v8("CL=F", client),
        _fetch_yahoo_v8("^GSPC", client),
        client.get(FX_URL, timeout=6.0),
        return_exceptions=True,
    )
    usd_eur = usd_gbp = usd_jpy = None
    if isinstance(fx_resp, httpx.Response) and fx_resp.status_code == 200:
        fx = fx_resp.json().get("rates", {})
        usd_eur = float(fx.get("EUR", 0.92))
        usd_gbp = float(fx.get("GBP", 0.79))
        usd_jpy = float(fx.get("JPY", 149.5))

    vix = vix if isinstance(vix, float) else None
    wti = wti if isinstance(wti, float) else None
    synth = _synthetic_macro()
    has_live_market = any(v is not None for v in (vix, wti))
    has_live_fx = usd_eur is not None

    return MacroData(
        vix=vix if vix is not None else synth.vix,
        wti_price=wti if wti is not None else synth.wti_price,
        sp500_change=0.0,
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
    departure_date: Optional[str] = None,
    return_date: Optional[str] = None,
    trip_type: str = "one_way",
    cabin_class: int = 1,
) -> LiveSeed:
    """Fetch all data sources concurrently and return a unified LiveSeed."""
    async with httpx.AsyncClient() as client:
        fare, demand, history, macro, origin_wx, dest_wx = await asyncio.gather(
            fetch_live_fare(origin, destination, client,
                            departure_date=departure_date, return_date=return_date,
                            trip_type=trip_type, cabin_class=cabin_class),
            fetch_route_demand(origin, destination, client),
            fetch_fare_history(origin, destination, client),
            fetch_macro(client),
            fetch_weather(origin, client, forecast_date=departure_date),
            fetch_weather(destination, client, forecast_date=departure_date),
        )

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
        fare=fare, demand=demand, history=history, macro=macro,
        trigger_id=trigger_id, route_label=f"{origin} → {destination}",
        disruption=_build_disruption(origin_wx, dest_wx),
    )


def build_live_seed_sync(
    origin: str,
    destination: str,
    trigger_id: str,
    macro_override: Optional[dict] = None,
    departure_date: Optional[str] = None,
    return_date: Optional[str] = None,
    trip_type: str = "one_way",
    cabin_class: int = 1,
) -> LiveSeed:
    """Synchronous wrapper for use inside Flask routes."""
    return asyncio.run(
        build_live_seed(
            origin, destination, trigger_id,
            macro_override=macro_override,
            departure_date=departure_date, return_date=return_date,
            trip_type=trip_type, cabin_class=cabin_class,
        )
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _next_friday() -> str:
    today = datetime.date.today()
    days_ahead = (4 - today.weekday()) % 7 or 7
    return (today + datetime.timedelta(days=days_ahead)).isoformat()
