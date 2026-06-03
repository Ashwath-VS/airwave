# AirWave — Airline Fare Scenario Intelligence

**Predict how a market shock ripples into airfare.** AirWave pulls live data, runs a deterministic cascade model, then dispatches 8 independent AI market agents — LCC revenue managers, legacy carriers, corporate buyers, OTAs, and more — each reasoning under the scenario conditions to produce a share-weighted consensus fare prediction.

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://python.org)
[![Vue](https://img.shields.io/badge/Vue-3-42b883)](https://vuejs.org)

---

## What it does

Pick a route (e.g. LHR → JFK), select a market trigger (Fuel Spike, Demand Collapse, Disruption Event…), and AirWave returns:

- **Predicted fare** with a ±confidence band
- **Fare delta %** from today's live price
- **Cascade breakdown** — how the shock propagates across fuel cost, crew, maintenance, slot fees, hedging P&L, and passenger yield
- **Agent consensus** — how 8 market participants each voted and why
- **Comparison mode** — stack two shock scenarios side-by-side with a winner verdict

---

## Architecture

```
Live Data Ingestion
  Duffel NDC fares · OpenSky demand · Open-Meteo weather
  Yahoo Finance macro · Google News RSS · Travelpayouts history
        ↓
Shock Cascade Engine (deterministic BFS — no LLM)
  Fuel cost · Crew · Maintenance · Slot fees · Hedge P&L · Passenger yield
        ↓
Multi-Agent Reasoning (Gemini 2.0/2.5 Flash)
  LCC RM · Legacy RM · ULCC RM · Premium Boutique
  Corporate Buyer · Leisure Traveler · OTA Platform · Miles Optimizer
        ↓
Share-Weighted Consensus Forecast
  Predicted fare · ±Prediction band · Agent agreement score
```

---

## Market Agents

| Agent | Represents | Hedge | Market Share |
|-------|-----------|-------|--------------|
| LCC Revenue Manager | Ryanair, easyJet, Spirit | 5% | 28% |
| Legacy Network Carrier | British Airways, Delta, Lufthansa | 75% | 42% |
| ULCC Revenue Manager | Wizz Air, Frontier, Allegiant | 0% | 12% |
| Premium Boutique | Emirates Business, Singapore Suites | 90% | 7% |
| Corporate Buyer | Fortune 500 travel procurement | — | demand-side |
| Leisure Traveler | Price-elastic consumer | — | demand-side |
| OTA Platform | Expedia, Google Flights | — | demand-side |
| Miles Optimizer | Loyalty power user | — | demand-side |

---

## Triggers

| Trigger | Data Source |
|---------|------------|
| Fuel Spike | WTI crude via Yahoo Finance (live) |
| Demand Collapse | Departure frequency via OpenSky Network (live) |
| Capacity Dump | Seat capacity via OpenSky (live) |
| Route Cancellation | Flight availability via SerpApi / Google Flights (live) |
| Exchange Rate | USD/EUR, GBP, JPY via open.exchangerate-api.com (live) |
| Disruption Event | Weather via Open-Meteo + network disruption patterns (live) |
| News Feed | Google News RSS — geopolitical, aviation, weather headlines (live) |

Stack multiple triggers for compounded shock scenarios.

---

## Quick Start

### Prerequisites

| Tool | Version |
|------|---------|
| Node.js | 18+ |
| Python | 3.11 or 3.12 |
| pip | latest |

### 1. Clone & configure

```bash
git clone https://github.com/YOUR_USERNAME/airwave.git
cd airwave

cp .env.example .env
# Fill in your API keys — see .env.example for all variables
```

### 2. Install dependencies

```bash
# Frontend
cd frontend && npm install && cd ..

# Backend
cd backend && pip install -r requirements.txt && cd ..
```

### 3. Run

```bash
# Backend (Flask) — from /backend
python run.py

# Frontend (Vite dev) — from /frontend
npm run dev
```

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:5001`

### 4. Build for production

```bash
cd frontend && npm run build
```

---

## API Reference

### `GET /health`
Returns `{ "status": "ok" }`.

### `GET /api/airwave/health`
Returns service status and data source availability.

### `GET /api/airwave/triggers`
Returns the list of available shock triggers with labels, icons, and data source descriptions.

### `GET /api/airwave/agents`
Returns the 8 agent profiles with behavioral metadata.

### `POST /api/airwave/simulate`
Run a full fare prediction simulation.

**Request body:**
```json
{
  "origin": "LHR",
  "destination": "JFK",
  "trigger_id": "FUEL_SPIKE",
  "trigger_ids": ["FUEL_SPIKE", "DISRUPTION_EVENT"],
  "depth": "standard",
  "departure_date": "2025-09-15",
  "return_date": "2025-09-22",
  "cabin": 1
}
```

`trigger_id` (single) or `trigger_ids` (array for stacked shocks). `depth` is one of `fast / standard / deep / exhaustive`.

**Rate limit:** 5 requests per 60 seconds per IP. Returns `429` with `Retry-After` header when exceeded.

### `POST /api/airwave/cascade`
Run only the deterministic cascade model (no agents, no LLM).

```json
{ "trigger_id": "FUEL_SPIKE" }
```

---

## Environment Variables

See `.env.example` for the full list. Key variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `LLM_API_KEY` | Yes | Gemini API key (Google AI Studio) |
| `LLM_BASE_URL` | Yes | LLM endpoint (default: Gemini) |
| `LLM_MODEL_NAME` | Yes | Model name (default: `gemini-2.5-flash`) |
| `SERPAPI_KEY` | No | Google Flights via SerpApi — live fare search |
| `TRAVELPAYOUTS_KEY` | No | Historical fare baseline data |
| `DUFFEL_API_KEY` | No | NDC fare offers (live airline fares) |
| `ZEP_API_KEY` | No | Agent long-term memory (not required for AirWave) |

The cascade engine and agent reasoning work without SerpApi/Travelpayouts/Duffel — fares fall back to synthetic estimation, which is clearly labeled in the UI.

---

## Project Structure

```
airwave/
├── frontend/                  # Vue 3 + Vite
│   ├── src/
│   │   ├── views/
│   │   │   └── SimulatorView.vue   # Main AirWave UI (all components inline)
│   │   └── api/
│   │       └── airwave.js          # API client
│   └── package.json
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── airwave.py          # Flask routes + rate limiter
│   │   ├── services/
│   │   │   ├── cascade_engine.py   # Deterministic BFS cascade model
│   │   │   ├── airline_simulator.py # 8-agent simulation harness
│   │   │   └── data_pipeline.py    # Live data ingestion
│   │   └── config.py               # Environment config + validation
│   ├── tests/
│   │   ├── test_airwave_api.py     # 18 API integration tests
│   │   └── test_cascade_engine.py  # 8 cascade unit tests
│   └── requirements.txt
│
└── .env.example
```

---

## Running Tests

```bash
cd backend
pip install pytest
pytest tests/ -v
```

26 tests covering: health endpoints, input validation, IATA checks, rate limiter (429 + Retry-After), cascade model (all triggers, field contracts, fare arithmetic), and stacked shock scenarios.

---

## Contributing

Pull requests are welcome. For significant changes, open an issue first to discuss the approach.

Areas of interest:
- Additional market triggers (regulatory changes, new entrant entry, alliance shifts)
- Historical backtesting against real fare data
- More regional airline agents (Middle East, Asia-Pacific)
- WebSocket streaming for long-running deep simulations
- Export to Excel / structured JSON report

---

## License

[AGPL-3.0](./LICENSE) — open source, copyleft.

---

*Built by [S·Ashwath](https://s-ashwath.com)*
