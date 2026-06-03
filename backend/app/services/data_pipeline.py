"""
AirWave Data Pipeline
Fetches live market data from SerpApi, OpenSky, Travelpayouts, Open-Meteo, and macro sources.
All functions gracefully degrade to synthetic baseline when API keys are absent.
"""

from __future__ import annotations

import asyncio
import datetime
import re
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


# ── Google Flights locale map ─────────────────────────────────────────────────
# Maps origin IATA → Google country code (gl=) so tax-inclusive fares are shown
# correctly (e.g. UK APD, EU taxes). Keeps hl=en so responses stay in English.
# Unmapped airports default to "us" (base-fare, no local tax surcharge).
AIRPORT_GL: dict[str, str] = {
    # United Kingdom
    "LHR": "gb", "LGW": "gb", "STN": "gb", "LTN": "gb",
    "MAN": "gb", "BHX": "gb", "EDI": "gb", "GLA": "gb",
    "LPL": "gb", "NCL": "gb", "BRS": "gb", "LBA": "gb",
    # Ireland
    "DUB": "ie", "SNN": "ie", "ORK": "ie",
    # Germany
    "FRA": "de", "MUC": "de", "BER": "de", "HAM": "de",
    "DUS": "de", "CGN": "de", "STR": "de", "NUE": "de",
    # France
    "CDG": "fr", "ORY": "fr", "LYS": "fr", "MRS": "fr",
    "NCE": "fr", "BOD": "fr", "TLS": "fr",
    # Netherlands
    "AMS": "nl", "RTM": "nl", "EIN": "nl",
    # Belgium
    "BRU": "be", "CRL": "be", "ANR": "be",
    # Switzerland
    "ZRH": "ch", "GVA": "ch", "BSL": "ch",
    # Austria
    "VIE": "at", "SZG": "at", "INN": "at",
    # Italy
    "FCO": "it", "MXP": "it", "LIN": "it", "NAP": "it",
    "VCE": "it", "BGY": "it", "PMO": "it",
    # Spain
    "MAD": "es", "BCN": "es", "AGP": "es", "PMI": "es",
    "VLC": "es", "SVQ": "es", "IBZ": "es",
    # Portugal
    "LIS": "pt", "OPO": "pt", "FAO": "pt",
    # Greece
    "ATH": "gr", "HER": "gr", "SKG": "gr", "CFU": "gr",
    # Scandinavia
    "OSL": "no", "BGO": "no",
    "ARN": "se", "GOT": "se",
    "CPH": "dk", "BLL": "dk",
    "HEL": "fi",
    # Eastern Europe
    "WAW": "pl", "KRK": "pl",
    "PRG": "cz",
    "BUD": "hu",
    "OTP": "ro",
    "SOF": "bg",
    "VIE": "at",
    # Middle East
    "DXB": "ae", "AUH": "ae", "SHJ": "ae",
    "DOH": "qa", "KWI": "kw", "BAH": "bh", "AHB": "sa",
    "RUH": "sa", "JED": "sa", "TLV": "il", "AMM": "jo",
    # Asia Pacific
    "HKG": "hk",
    "SIN": "sg",
    "BKK": "th", "HKT": "th", "CNX": "th",
    "KUL": "my", "PEN": "my",
    "CGK": "id", "DPS": "id",
    "MNL": "ph", "CEB": "ph",
    "SGN": "vn", "HAN": "vn",
    "HND": "jp", "NRT": "jp", "KIX": "jp", "FUK": "jp",
    "ICN": "kr", "GMP": "kr",
    "PEK": "cn", "PVG": "cn", "CAN": "cn", "CTU": "cn",
    "BOM": "in", "DEL": "in", "MAA": "in", "BLR": "in",
    "HYD": "in", "CCU": "in", "COK": "in",
    "CMB": "lk",
    "KTM": "np",
    "DAC": "bd",
    "KHI": "pk", "LHE": "pk", "ISB": "pk",
    "SYD": "au", "MEL": "au", "BNE": "au", "PER": "au",
    "ADL": "au", "CBR": "au",
    "AKL": "nz", "CHC": "nz",
    # Canada
    "YYZ": "ca", "YVR": "ca", "YUL": "ca", "YYC": "ca",
    "YEG": "ca", "YOW": "ca", "YHZ": "ca",
    # Latin America
    "EZE": "ar", "AEP": "ar",
    "GRU": "br", "GIG": "br", "BSB": "br", "SSA": "br",
    "BOG": "co", "MDE": "co",
    "SCL": "cl",
    "LIM": "pe",
    "UIO": "ec", "GYE": "ec",
    "MVD": "uy",
    "CCS": "ve",
    "MEX": "mx", "CUN": "mx", "GDL": "mx",
    "PTY": "pa",
    "SJO": "cr",
    "SAL": "sv",
    "GUA": "gt",
    "SDQ": "do", "PUJ": "do",
    "HAV": "cu",
    # Africa
    "JNB": "za", "CPT": "za", "DUR": "za",
    "NBO": "ke", "MBA": "ke",
    "DAR": "tz", "ZNZ": "tz",
    "ADD": "et",
    "ACC": "gh",
    "LOS": "ng", "ABV": "ng",
    "CMN": "ma", "RAK": "ma",
    "TUN": "tn",
    "ALG": "dz",
    "CAI": "eg", "SSH": "eg", "HRG": "eg",
    "CPT": "za",
    # US — all default to "us" but list key hubs explicitly
    "JFK": "us", "LAX": "us", "ORD": "us", "ATL": "us",
    "DFW": "us", "SFO": "us", "BOS": "us", "MIA": "us",
    "EWR": "us", "SEA": "us", "IAD": "us", "DCA": "us",
    "LAS": "us", "DEN": "us", "PHX": "us", "CLT": "us",
    "MSP": "us", "DTW": "us", "PHL": "us", "SLC": "us",
    "BWI": "us", "MDW": "us", "HOU": "us", "FLL": "us",
    "SAN": "us", "TPA": "us", "PDX": "us", "HNL": "us",
    "AUS": "us", "BNA": "us", "STL": "us", "MCI": "us",
    "RDU": "us", "CLE": "us", "IND": "us", "CMH": "us",
    "PIT": "us", "MEM": "us", "MKE": "us", "OMA": "us",
}


def _airport_gl(iata: str) -> str:
    """Return the Google country code (gl=) for a given origin IATA code.

    Drives tax-inclusive fare display: UK searches include APD, EU searches
    include local aviation taxes, matching what Skyscanner/Expedia show users
    in those countries. Falls back to 'us' (base fare, no surcharges) for
    unmapped airports.
    """
    return AIRPORT_GL.get(iata.upper(), "us")


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
    available_flights: list = field(default_factory=list)  # top 5 flight options from SerpApi


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


# ── Shared helpers ────────────────────────────────────────────────────────────

_CABIN_DUFFEL: dict[int, str] = {
    1: "economy", 2: "premium_economy", 3: "business", 4: "first"
}
_CABIN_KIWI: dict[int, str] = {
    1: "M", 2: "W", 3: "C", 4: "F"
}


def _fare_from_option(opt: dict, origin: str, destination: str,
                      outbound: str, return_date: Optional[str],
                      trip_type: str, cabin_class: int, source: str) -> FareData:
    """Build a FareData from a normalised option dict."""
    return FareData(
        origin=origin, destination=destination,
        current_price_usd=opt["price_usd"], source=source,
        departure_date=outbound, return_date=return_date,
        trip_type=trip_type, cabin_class=cabin_class,
        airline_name=opt.get("airline_name", ""),
        airline_logo=opt.get("airline_logo", ""),
        flight_number=opt.get("flight_number", ""),
        departure_time=opt.get("departure_time", ""),
        arrival_time=opt.get("arrival_time", ""),
        duration_min=int(opt.get("duration_min") or 0),
        is_direct=bool(opt.get("is_direct", True)),
        arrives_next_day=bool(opt.get("arrives_next_day", False)),
        origin_airport_name=opt.get("origin_airport_name", ""),
        dest_airport_name=opt.get("dest_airport_name", ""),
        num_stops=int(opt.get("num_stops") or 0),
    )


# ── Layer 1: Duffel — NDC airline fares (most accurate, bookable prices) ──────
# Duffel connects directly to airlines via NDC — same inventory as Expedia/Kayak.
# Flow: POST /air/offer_requests → wait for offers → parse best 5 by price.
# Auth: Authorization: Bearer duffel_live_... (or duffel_test_... for sandbox)
# Sign up: https://app.duffel.com/join  (free account, generate live token in dashboard)

_DUFFEL_BASE = "https://api.duffel.com"
_DUFFEL_VERSION = "v2"


async def _fetch_duffel(
    origin: str,
    destination: str,
    client: httpx.AsyncClient,
    departure_date: Optional[str] = None,
    return_date: Optional[str] = None,
    trip_type: str = "one_way",
    cabin_class: int = 1,
) -> tuple[FareData, list[dict]] | None:
    """Fetch fares from Duffel NDC API. Returns None if unconfigured or no results."""
    key = Config.DUFFEL_API_KEY
    if not key or key.startswith("FILL_IN"):
        return None

    outbound = departure_date or _next_friday()
    cabin = _CABIN_DUFFEL.get(cabin_class, "economy")

    # Build slices — one-way or round-trip
    slices: list[dict] = [
        {"origin": origin, "destination": destination, "departure_date": outbound}
    ]
    if trip_type == "round_trip" and return_date:
        slices.append(
            {"origin": destination, "destination": origin, "departure_date": return_date}
        )

    headers = {
        "Authorization": f"Bearer {key}",
        "Duffel-Version": _DUFFEL_VERSION,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    body = {
        "data": {
            "slices": slices,
            "passengers": [{"type": "adult"}],
            "cabin_class": cabin,
        }
    }

    try:
        # Step 1 — create offer request (Duffel returns 201 Created on success)
        resp = await client.post(
            f"{_DUFFEL_BASE}/air/offer_requests",
            json=body,
            headers=headers,
            timeout=30.0,
        )
        if resp.status_code not in (200, 201):
            logger.warning(f"Duffel offer_request error {resp.status_code}: {resp.text[:300]}")
            return None

        payload = resp.json()
        request_data = payload.get("data") or {}
        offers = request_data.get("offers") or []

        # Offers are returned inline in the offer_request response.
        # If empty (shouldn't happen in normal flow), fall back to listing endpoint.
        if not offers:
            req_id = request_data.get("id", "")
            if req_id:
                list_resp = await client.get(
                    f"{_DUFFEL_BASE}/air/offers",
                    params={"offer_request_id": req_id, "sort": "total_amount", "limit": 10},
                    headers=headers,
                    timeout=20.0,
                )
                if list_resp.status_code == 200:
                    offers = list_resp.json().get("data") or []

        if not offers:
            return None

        # Resolve FX rate once if account currency != USD
        # Duffel returns prices in the account's configured currency (often GBP/EUR).
        sample_currency = (offers[0].get("total_currency") or "USD").upper()
        usd_rate = 1.0   # default: assume USD
        if sample_currency != "USD":
            try:
                fx_resp = await client.get(FX_URL, timeout=6.0)
                if fx_resp.status_code == 200:
                    rates = fx_resp.json().get("rates", {})
                    rate_to_usd = rates.get("USD", 1.0) / rates.get(sample_currency, 1.0)
                    usd_rate = float(rate_to_usd)
                    logger.debug(f"Duffel currency: {sample_currency} → USD rate {usd_rate:.4f}")
            except Exception:
                # Hardcoded emergency fallbacks
                fallback = {"GBP": 1.27, "EUR": 1.09, "CAD": 0.74, "AUD": 0.65, "JPY": 0.0067}
                usd_rate = fallback.get(sample_currency, 1.0)

        options: list[dict] = []
        for offer in offers:
            try:
                price_native = float(offer.get("total_amount") or 0)
                if price_native <= 0:
                    continue
                price_usd = round(price_native * usd_rate, 2)

                offer_slices = offer.get("slices") or []
                if not offer_slices:
                    continue
                out_slice = offer_slices[0]
                segments = out_slice.get("segments") or []
                if not segments:
                    continue
                first_seg = segments[0]
                last_seg  = segments[-1]
                num_stops = max(0, len(segments) - 1)
                carrier   = first_seg.get("marketing_carrier") or {}
                dep_raw   = first_seg.get("departing_at", "")
                arr_raw   = last_seg.get("arriving_at", "")
                dep_date_str = dep_raw[:10] if dep_raw else ""
                arr_date_str = arr_raw[:10] if arr_raw else ""

                # Sum ISO-8601 durations: PT4H35M → 275 min
                total_min = 0
                for seg in segments:
                    dur = seg.get("duration") or ""
                    h_m = re.search(r'(\d+)H', dur)
                    m_m = re.search(r'(\d+)M', dur)
                    total_min += (int(h_m.group(1)) if h_m else 0) * 60
                    total_min += (int(m_m.group(1)) if m_m else 0)

                options.append({
                    "airline_name":       carrier.get("name", ""),
                    "airline_logo":       carrier.get("logo_symbol_url", ""),
                    "flight_number":      f"{carrier.get('iata_code','')}{first_seg.get('marketing_carrier_flight_number','')}",
                    "departure_time":     dep_raw[11:16] if len(dep_raw) >= 16 else "",
                    "arrival_time":       arr_raw[11:16] if len(arr_raw) >= 16 else "",
                    "duration_min":       total_min,
                    "is_direct":          num_stops == 0,
                    "num_stops":          num_stops,
                    "price_usd":          price_usd,
                    "arrives_next_day":   bool(dep_date_str and arr_date_str and dep_date_str != arr_date_str),
                    "origin_airport_name": (out_slice.get("origin") or {}).get("name", ""),
                    "dest_airport_name":   (out_slice.get("destination") or {}).get("name", ""),
                    "departure_date":     outbound,
                    "return_date":        return_date,
                    "trip_type":          trip_type,
                    "cabin_class":        cabin_class,
                })
                if len(options) >= 5:
                    break
            except Exception as parse_err:
                logger.debug(f"Duffel offer parse error: {parse_err}")
                continue

        if options:
            options.sort(key=lambda o: o["price_usd"])
            source = "duffel" if not key.startswith("duffel_test_") else "duffel/test"
            fare = _fare_from_option(options[0], origin, destination,
                                     outbound, return_date, trip_type, cabin_class,
                                     source=source)
            logger.info(f"Duffel: {origin}→{destination} ${options[0]['price_usd']:.0f} "
                        f"({options[0]['airline_name']}) [{len(options)} offers] [{source}]")
            return fare, options

    except Exception as e:
        logger.warning(f"Duffel fetch failed ({origin}→{destination}): {e}")
    return None


# ── Layer 2: Kiwi Tequila — aggregated real fares ─────────────────────────────
# Kiwi aggregates from GDS + direct airline connections. Good global coverage.
# Auth: apikey header (single key, no OAuth).
# Sign up: https://tequila.kiwi.com/portal  (free tier available)

async def _fetch_kiwi(
    origin: str,
    destination: str,
    client: httpx.AsyncClient,
    departure_date: Optional[str] = None,
    return_date: Optional[str] = None,
    trip_type: str = "one_way",
    cabin_class: int = 1,
) -> tuple[FareData, list[dict]] | None:
    """Fetch fares from Kiwi Tequila API. Returns None if unconfigured or no results."""
    key = Config.KIWI_API_KEY
    if not key or key.startswith("FILL_IN"):
        return None

    outbound = departure_date or _next_friday()
    cabin = _CABIN_KIWI.get(cabin_class, "M")

    def _to_kiwi_date(iso: str) -> str:
        """Convert YYYY-MM-DD to dd/mm/yyyy expected by Kiwi."""
        try:
            y, m, d = iso.split("-")
            return f"{d}/{m}/{y}"
        except Exception:
            return iso

    params: dict = {
        "fly_from": origin,
        "fly_to": destination,
        "date_from": _to_kiwi_date(outbound),
        "date_to": _to_kiwi_date(outbound),
        "selected_cabins": cabin,
        "curr": "USD",
        "limit": 5,
        "sort": "price",
        "asc": 1,
        "one_for_city": 1,
        "partner_market": _airport_gl(origin),
    }
    if trip_type == "round_trip" and return_date:
        params["return_from"] = _to_kiwi_date(return_date)
        params["return_to"] = _to_kiwi_date(return_date)

    try:
        resp = await client.get(
            "https://api.tequila.kiwi.com/v2/search",
            params=params,
            headers={"apikey": key},
            timeout=15.0,
        )
        resp.raise_for_status()
        flights = resp.json().get("data") or []

        options: list[dict] = []
        for f in flights:
            price = float(f.get("price") or 0)
            if price <= 0:
                continue
            route = f.get("route") or []
            first_seg = route[0] if route else {}
            last_seg = route[-1] if route else {}
            num_stops = max(0, len(route) - 1)
            dep_raw = first_seg.get("local_departure", "")
            arr_raw = last_seg.get("local_arrival", "")
            dep_date_str = dep_raw[:10] if dep_raw else ""
            arr_date_str = arr_raw[:10] if arr_raw else ""
            duration_sec = (f.get("duration") or {}).get("departure") or 0
            airline_code = first_seg.get("airline", "")
            options.append({
                "airline_name": airline_code,   # Kiwi returns IATA code; full name not in free tier
                "airline_logo": f"https://images.kiwi.com/airlines/64/{airline_code}.png",
                "flight_number": f"{airline_code}{first_seg.get('flight_no', '')}",
                "departure_time": dep_raw[11:16] if len(dep_raw) >= 16 else "",
                "arrival_time": arr_raw[11:16] if len(arr_raw) >= 16 else "",
                "duration_min": int(duration_sec // 60) if duration_sec else 0,
                "is_direct": num_stops == 0,
                "num_stops": num_stops,
                "price_usd": price,
                "arrives_next_day": bool(dep_date_str and arr_date_str and dep_date_str != arr_date_str),
                "origin_airport_name": first_seg.get("flyFrom", origin),
                "dest_airport_name": last_seg.get("flyTo", destination),
                "departure_date": outbound,
                "return_date": return_date,
                "trip_type": trip_type,
                "cabin_class": cabin_class,
            })
            if len(options) >= 5:
                break

        if options:
            fare = _fare_from_option(options[0], origin, destination,
                                     outbound, return_date, trip_type, cabin_class,
                                     source="kiwi")
            logger.info(f"Kiwi: {origin}→{destination} ${options[0]['price_usd']:.0f} "
                        f"({options[0]['airline_name']}) [{len(options)} results]")
            return fare, options

    except Exception as e:
        logger.warning(f"Kiwi fetch failed ({origin}→{destination}): {e}")
    return None


# ── Layer 3: SerpAPI — Google Flights (locale-aware) ─────────────────────────

def _flight_group_to_option(group: dict, outbound: str, return_date: Optional[str],
                             trip_type: str, cabin_class: int,
                             origin: str, destination: str) -> Optional[dict]:
    """Parse a SerpApi flight group into a normalised option dict."""
    price = group.get("price", 0)
    if not price or price <= 0:
        return None
    flights_list = group.get("flights") or []
    first_leg = flights_list[0] if flights_list else {}
    last_leg = flights_list[-1] if flights_list else {}
    dep_airport = first_leg.get("departure_airport", {})
    arr_airport = last_leg.get("arrival_airport", {})
    dep_raw = dep_airport.get("time", "")
    arr_raw = arr_airport.get("time", "")
    dep_date = dep_raw[:10] if dep_raw else ""
    arr_date = arr_raw[:10] if arr_raw else ""
    num_stops = max(0, len(flights_list) - 1)
    return {
        "airline_name": first_leg.get("airline", ""),
        "airline_logo": first_leg.get("airline_logo", ""),
        "flight_number": first_leg.get("flight_number", ""),
        "departure_time": _parse_flight_time(dep_raw),
        "arrival_time": _parse_flight_time(arr_raw),
        "duration_min": int(group.get("total_duration") or 0),
        "is_direct": num_stops == 0,
        "num_stops": num_stops,
        "price_usd": float(price),
        "arrives_next_day": bool(dep_date and arr_date and dep_date != arr_date),
        "origin_airport_name": dep_airport.get("name", ""),
        "dest_airport_name": arr_airport.get("name", ""),
        "departure_date": outbound,
        "return_date": return_date,
        "trip_type": trip_type,
        "cabin_class": cabin_class,
    }


async def _fetch_serpapi(
    origin: str,
    destination: str,
    client: httpx.AsyncClient,
    departure_date: Optional[str] = None,
    return_date: Optional[str] = None,
    trip_type: str = "one_way",
    cabin_class: int = 1,
) -> tuple[FareData, list[dict]] | None:
    """Fetch fares from SerpAPI (Google Flights). Returns None if unconfigured or no results."""
    key = Config.SERPAPI_KEY
    if not key or key.startswith("FILL_IN"):
        return None

    outbound = departure_date or _next_friday()
    search_type = "1" if trip_type == "round_trip" and return_date else "2"
    gl = _airport_gl(origin)
    params: dict = {
        "engine": "google_flights",
        "departure_id": origin, "arrival_id": destination,
        "outbound_date": outbound, "type": search_type,
        "travel_class": cabin_class, "currency": "USD",
        "hl": "en", "gl": gl,
        "api_key": key,
    }
    if search_type == "1" and return_date:
        params["return_date"] = return_date

    try:
        resp = await client.get("https://serpapi.com/search", params=params, timeout=15.0)
        resp.raise_for_status()
        data = resp.json()
        all_groups = (data.get("best_flights") or []) + (data.get("other_flights") or [])

        options: list[dict] = []
        for grp in all_groups:
            opt = _flight_group_to_option(grp, outbound, return_date, trip_type, cabin_class,
                                          origin, destination)
            if opt:
                options.append(opt)
            if len(options) >= 5:
                break

        if options:
            fare = _fare_from_option(options[0], origin, destination,
                                     outbound, return_date, trip_type, cabin_class,
                                     source=f"serpapi/{gl}")
            logger.info(f"SerpAPI: {origin}→{destination} ${options[0]['price_usd']:.0f} "
                        f"({options[0]['airline_name']}) [{len(options)} results]")
            return fare, options

    except Exception as e:
        logger.warning(f"SerpApi fetch failed ({origin}→{destination}): {e}")
    return None


# ── Fare fetcher — 4-layer fallback chain ─────────────────────────────────────

async def _fetch_flights_raw(
    origin: str,
    destination: str,
    client: httpx.AsyncClient,
    departure_date: Optional[str] = None,
    return_date: Optional[str] = None,
    trip_type: str = "one_way",
    cabin_class: int = 1,
) -> tuple[FareData, list[dict]]:
    """
    Fetch fares using a 4-layer fallback chain:
      1. Duffel  — NDC airline fares, same source as Expedia/Kayak (needs duffel_live_... key)
      2. Kiwi    — Kiwi.com aggregated real fares (needs KIWI_API_KEY)
      3. SerpAPI — Google Flights, locale-aware tax inclusion (needs SERPAPI_KEY)
      4. Synthetic — hash-based estimate, flagged as estimated in UI

    Configure keys in .env; any layer without a key is silently skipped.
    """
    outbound = departure_date or _next_friday()
    kwargs = dict(departure_date=departure_date, return_date=return_date,
                  trip_type=trip_type, cabin_class=cabin_class)

    # Layer 1: Duffel
    result = await _fetch_duffel(origin, destination, client, **kwargs)
    if result:
        return result

    # Layer 2: Kiwi Tequila
    result = await _fetch_kiwi(origin, destination, client, **kwargs)
    if result:
        return result

    # Layer 3: SerpAPI (Google Flights)
    result = await _fetch_serpapi(origin, destination, client, **kwargs)
    if result:
        return result

    # Layer 4: Synthetic fallback — deterministic estimate, clearly flagged
    logger.warning(f"All fare sources failed for {origin}→{destination} — using synthetic estimate")
    fare = _synthetic_fare(origin, destination)
    fare.departure_date = outbound
    fare.return_date = return_date
    fare.trip_type = trip_type
    fare.cabin_class = cabin_class
    return fare, []


async def fetch_live_fare(
    origin: str,
    destination: str,
    client: httpx.AsyncClient,
    departure_date: Optional[str] = None,
    return_date: Optional[str] = None,
    trip_type: str = "one_way",
    cabin_class: int = 1,
) -> FareData:
    """Backwards-compatible wrapper — returns only the best FareData."""
    fare, _ = await _fetch_flights_raw(
        origin, destination, client,
        departure_date=departure_date, return_date=return_date,
        trip_type=trip_type, cabin_class=cabin_class,
    )
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
        all_dest_data = data.get("data") or {}

        # Travelpayouts returns data keyed by city code (e.g. "NYC" for JFK/LGA/EWR).
        # Try exact airport code first, then fall back to any key in the response.
        prices = all_dest_data.get(destination) or {}
        if not prices and all_dest_data:
            prices = next(iter(all_dest_data.values()), {})

        if prices:
            values = [v.get("price", 0) for v in prices.values() if v.get("price")]
            if values:
                avg = sum(values) / len(values)
                latest = values[0]
                trend = (latest - avg) / avg if avg > 0 else 0.0
                logger.info(f"Travelpayouts: {origin}->{destination} baseline=${avg:.0f} "
                            f"({len(values)} data points, trend {trend*100:+.1f}%)")
                return HistoricalFare(
                    origin=origin, destination=destination,
                    baseline_price_usd=round(avg, 2), month_avg=round(avg, 2),
                    price_trend=round(trend, 4), source="travelpayouts",
                )
    except Exception as e:
        logger.warning(f"Travelpayouts fetch failed ({origin}->{destination}): {e}")
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
        (fare, available_flights), demand, history, macro, origin_wx, dest_wx = await asyncio.gather(
            _fetch_flights_raw(origin, destination, client,
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

    # Re-anchor synthetic history to the live fare so the "vs current fare"
    # comparison is meaningful. The hash-based fallback ($320-670) is designed
    # for generic North-Atlantic routes; it's wildly wrong for short-haul or
    # domestic routes (e.g. DEL-BLR at $60). When we have a real fare but no
    # Travelpayouts data, estimate the baseline as ±15% of the live fare using
    # a deterministic route hash — keeps comparison within ±25% of reality.
    if history.source == "synthetic" and fare.source not in ("synthetic",):
        live_price = fare.current_price_usd
        h = abs(hash(f"hist{origin}{destination}")) % 100  # deterministic 0..99
        # factor in 0.88 … 1.12 range so baseline is ±12% of live fare
        factor = 0.88 + (h / 100) * 0.24
        base = round(live_price * factor, 2)
        month_avg = round(base * 1.04, 2)          # monthly avg ~4% higher than point-in-time
        price_trend = round((base / month_avg) - 1.0, 4)  # current vs monthly avg
        history = HistoricalFare(
            origin=origin, destination=destination,
            baseline_price_usd=base, month_avg=month_avg,
            price_trend=price_trend, source="estimated",
        )
        logger.info(
            f"History re-anchored to live fare: {origin}->{destination} "
            f"live=${live_price:.0f} baseline=${base:.0f} (factor={factor:.2f})"
        )

    return LiveSeed(
        fare=fare, demand=demand, history=history, macro=macro,
        trigger_id=trigger_id, route_label=f"{origin} → {destination}",
        disruption=_build_disruption(origin_wx, dest_wx),
        available_flights=available_flights,
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
