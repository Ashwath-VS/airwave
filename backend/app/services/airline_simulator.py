"""
AirWave Airline Simulator
MiroFish-pattern multi-agent simulation for airline fare prediction.

Four airline market agents with distinct personalities interact over N rounds
in response to a macro shock. Each round each agent:
  1. Observes current market state
  2. Makes a pricing/operational decision
  3. Reacts to other agents' previous decisions (social evolution)

After all rounds, a prediction parser extracts the quantitative fare delta
and a confidence interval from the agent narrative outputs.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ..config import Config
from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger
from .cascade_engine import NodeImpact, run_cascade
from .data_pipeline import LiveSeed

logger = get_logger("airwave.simulator")


# ── Agent definitions ─────────────────────────────────────────────────────────

@dataclass
class Agent:
    id: str
    name: str
    role: str
    personality: str
    constraints: str
    hedge_ratio: float = 0.0   # 0 = unhedged, 1 = fully hedged
    market_share: float = 0.0  # 0–1


AIRLINE_AGENTS: list[Agent] = [
    Agent(
        id="lcc_rm",
        name="Riley Chen",
        role="Revenue Manager, Low-Cost Carrier",
        personality=(
            "Aggressive yield manager at a lean LCC. Unhedged on fuel. "
            "Reacts fast — raises fares on leisure routes within 48h of any cost shock. "
            "Watches load factor obsessively. Willing to sacrifice premium for volume."
        ),
        constraints="No corporate contracts. No long-haul. GDS distribution minimal (NDC-first).",
        hedge_ratio=0.05,
        market_share=0.28,
    ),
    Agent(
        id="legacy_rm",
        name="Marcus Webb",
        role="Revenue Manager, Legacy Network Carrier",
        personality=(
            "Conservative RM at a full-service carrier. 75% fuel hedged for next 90 days. "
            "Protects business class yield above all. Watches LCC pricing before moving. "
            "Raises fares 7–14 days after LCC moves. Corporate contracts create pricing floors."
        ),
        constraints="Hub-and-spoke constraints. GDS-heavy distribution. IATA fare rules apply.",
        hedge_ratio=0.75,
        market_share=0.42,
    ),
    Agent(
        id="corporate_buyer",
        name="Priya Sharma",
        role="Corporate Travel Manager, Fortune 500",
        personality=(
            "Manages $40M annual travel budget. Switches carriers when price delta exceeds 12%. "
            "Books 45–60 days in advance. Prioritises schedule reliability over lowest fare. "
            "Has preferred-carrier agreements but will break them for significant savings."
        ),
        constraints="Policy: Economy for <4h, Business for >4h. Approval required for rebooking.",
        hedge_ratio=0.0,
        market_share=0.0,
    ),
    Agent(
        id="leisure_traveler",
        name="Sam Park",
        role="Leisure Traveler / Price-Elastic Consumer",
        personality=(
            "Flexible dates, price-driven. Postpones booking when fares rise >15%. "
            "Books last-minute when prices drop. Uses Google Flights price alerts. "
            "Highly elastic — a 20% fare hike reduces booking probability by 35%."
        ),
        constraints="Budget: max $800 for domestic, $1,800 for international.",
        hedge_ratio=0.0,
        market_share=0.0,
    ),
    Agent(
        id="ulcc_rm",
        name="Yara Okonkwo",
        role="Revenue Manager, Ultra-Low Cost Carrier",
        personality=(
            "Hyper-aggressive yield manager at a ULCC. Zero fuel hedging whatsoever. "
            "Primary revenue lever is ancillary: seat selection, bags, priority boarding. "
            "Will slash base fares to near-zero to capture volume and outflank LCCs, "
            "then recover margin through unbundled extras. "
            "Reacts to any demand signal within 24 hours — faster than any other carrier."
        ),
        constraints=(
            "No checked bags included. All ancillaries strictly unbundled. "
            "Primary distribution: own website, no GDS. Operates thin margins on every route."
        ),
        hedge_ratio=0.0,
        market_share=0.12,
    ),
    Agent(
        id="premium_boutique",
        name="Elena Vasquez",
        role="Network Pricing Director, Premium Boutique Airline",
        personality=(
            "Curates a premium niche product with loyal high-yield clientele. "
            "Never competes on price — protects fare integrity and brand positioning above all. "
            "Will hold fares stable or add product value (lounge access, flexibility waivers) "
            "rather than discount even under significant fare pressure from competitors. "
            "Corporate accounts are locked in; leisure demand is secondary."
        ),
        constraints=(
            "Limited fleet, premium routes only. 90% fuel hedged for 180 days. "
            "Corporate accounts carry fixed-rate agreements that cannot be adjusted mid-quarter."
        ),
        hedge_ratio=0.90,
        market_share=0.07,
    ),
    Agent(
        id="ota_platform",
        name="Nikos Papadopoulos",
        role="Chief Merchandising Officer, Online Travel Agency",
        personality=(
            "Aggregates inventory across 40+ airlines. Optimises for conversion rate and "
            "GDS commission per booking. When fares spike, re-ranks cheaper alternatives "
            "and fires price-drop alerts to 50M+ registered users, amplifying demand shifts. "
            "Actively merchandises 'deal' fares from capacity-dumping carriers. "
            "No airline loyalty — pure margin maximisation per search click."
        ),
        constraints=(
            "Must display best available published fare. No exclusive inventory access. "
            "GDS-dependent; NDC integrations partial. Must comply with screen-scraping T&Cs."
        ),
        hedge_ratio=0.0,
        market_share=0.0,
    ),
    Agent(
        id="miles_optimizer",
        name="Tariq Al-Hassan",
        role="Frequent Flyer / Points & Miles Optimizer",
        personality=(
            "Exclusively books premium cabins using miles and credit-card points. "
            "Tracks award-space openings obsessively across multiple loyalty programs. "
            "A cash-fare spike above 10% immediately triggers a points redemption search — "
            "pulling demand from the revenue booking pool into award inventory. "
            "Shares award findings with a 200K-follower community, creating demand ripples."
        ),
        constraints=(
            "Points + miles budget: ~500K points annually. "
            "Prefers nonstop routes for award availability. "
            "Booking window: 30–45 days out for premium cabin saver awards."
        ),
        hedge_ratio=0.0,
        market_share=0.0,
    ),
]


# ── Simulation state ──────────────────────────────────────────────────────────

@dataclass
class AgentAction:
    round_num: int
    agent_id: str
    agent_name: str
    decision: str          # e.g. "raise_fares", "hold_fares", "delay_booking"
    magnitude: float       # fare delta as fraction, e.g. 0.12 = +12%
    reasoning: str
    confidence: float      # 0–1


@dataclass
class SimulationResult:
    simulation_id: str
    trigger_id: str
    route: str
    rounds: int
    seed_fare: float
    predicted_fare: float
    fare_delta: float           # fraction, e.g. 0.12 = +12%
    confidence: float           # 0–1
    days_to_effect: int
    agent_consensus: str        # "strong_raise" | "moderate_raise" | "hold" | "moderate_drop" | "strong_drop"
    actions: list[AgentAction]
    cascade_impacts: dict[str, Any]
    narrative: str
    sources: dict[str, str]     # which data sources were live vs synthetic
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


# ── Simulator ─────────────────────────────────────────────────────────────────

class AirlineSimulator:
    """
    Multi-agent airline fare prediction simulation.

    Mirrors MiroFish's pattern:
      seed → environment setup → N rounds of agent interaction → prediction report
    """

    def __init__(self) -> None:
        self.llm = LLMClient()
        self.rounds = Config.SIMULATION_DEFAULT_ROUNDS

    def run(
        self,
        seed: LiveSeed,
        simulation_id: str,
        rounds: int | None = None,
        trigger_ids: list[str] | None = None,
        news_context: list[str] | None = None,
    ) -> SimulationResult:
        """
        Run the full simulation and return a prediction result.
        trigger_ids: if provided, cascade runs on all of them (combined shock).
        """
        n_rounds = rounds or self.rounds
        effective_triggers = trigger_ids or [seed.trigger_id]
        logger.info(
            f"Starting simulation: id={simulation_id}, "
            f"route={seed.route_label}, triggers={effective_triggers}, rounds={n_rounds}"
        )

        # Step 1: cascade model outputs (multi-trigger if provided)
        cascade = run_cascade(effective_triggers)
        logger.info(f"Cascade computed: {len(cascade)} nodes affected")

        # Step 2: build simulation context
        context = self._build_context(seed, cascade, news_context or [])

        # Step 3: run agent rounds
        actions: list[AgentAction] = []
        market_state = {
            "current_price": seed.fare.current_price_usd,
            "demand_index": seed.demand.demand_index,
            "lcc_last_move": 0.0,
            "legacy_last_move": 0.0,
        }
        # Build an index for ordering agent results deterministically
        _agent_order = {a.id: i for i, a in enumerate(AIRLINE_AGENTS)}

        llm_failures = 0
        total_calls = n_rounds * len(AIRLINE_AGENTS)

        for round_num in range(1, n_rounds + 1):
            logger.info(f"Round {round_num}/{n_rounds} — running {len(AIRLINE_AGENTS)} agents in parallel")
            # Snapshot state before the round so all agents see the same context
            snapshot_actions = list(actions)
            snapshot_market = dict(market_state)
            round_results: list[AgentAction] = []

            with ThreadPoolExecutor(max_workers=len(AIRLINE_AGENTS)) as executor:
                futures = {
                    executor.submit(
                        self._agent_turn, agent, round_num, context,
                        snapshot_market, snapshot_actions
                    ): agent
                    for agent in AIRLINE_AGENTS
                }
                for future in as_completed(futures):
                    action = future.result()
                    if "LLM unavailable" in action.reasoning or "Error — defaulting" in action.reasoning:
                        llm_failures += 1
                    round_results.append(action)

            # Sort results in canonical agent order for deterministic output
            round_results.sort(key=lambda a: _agent_order.get(a.agent_id, 99))

            # Apply round results to market state
            for action in round_results:
                actions.append(action)
                if action.agent_id == "lcc_rm":
                    market_state["lcc_last_move"] = action.magnitude
                elif action.agent_id == "legacy_rm":
                    market_state["legacy_last_move"] = action.magnitude
                ag = next((a for a in AIRLINE_AGENTS if a.id == action.agent_id), None)
                if ag and action.decision in ("raise_fares", "drop_fares"):
                    market_state["current_price"] *= (1 + action.magnitude * ag.market_share)

        # If more than half the agents couldn't call the LLM, the simulation is
        # unreliable — surface a hard error rather than returning fictitious results
        if llm_failures > total_calls * 0.5:
            raise RuntimeError(
                f"Agent simulation failed: {llm_failures}/{total_calls} LLM calls returned errors. "
                "Possible causes: API rate limit exceeded, invalid API key, or network issue. "
                "Check your LLM_API_KEY in .env and try again in 30 seconds."
            )

        # Step 4: extract quantitative prediction
        fare_delta, confidence, days = self._extract_prediction(actions, cascade)
        predicted_fare = seed.fare.current_price_usd * (1 + fare_delta)
        consensus = self._consensus_label(fare_delta, confidence)

        # Step 5: generate narrative report
        narrative = self._generate_report(seed, cascade, actions, fare_delta, confidence)

        return SimulationResult(
            simulation_id=simulation_id,
            trigger_id=seed.trigger_id,
            route=seed.route_label,
            rounds=n_rounds,
            seed_fare=round(seed.fare.current_price_usd, 2),
            predicted_fare=round(predicted_fare, 2),
            fare_delta=round(fare_delta, 4),
            confidence=round(confidence, 2),
            days_to_effect=days,
            agent_consensus=consensus,
            actions=actions,
            cascade_impacts={k: {
                "impact": v.impact,
                "confidence": v.confidence,
                "days_to_effect": v.days_to_effect,
                "mechanism": v.mechanism,
                "recovery": v.recovery,
            } for k, v in cascade.items()},
            narrative=narrative,
            sources={
                "fare": seed.fare.source,
                "demand": seed.demand.source,
                "history": seed.history.source,
                "macro": seed.macro.source,
            },
        )

    # ── Private helpers ────────────────────────────────────────────────────────

    def _build_context(self, seed: LiveSeed, cascade: dict[str, NodeImpact], news_context: list[str] | None = None) -> str:
        top_impacts = sorted(
            cascade.values(), key=lambda x: abs(x.impact), reverse=True
        )[:5]
        impact_lines = "\n".join(
            f"  - {n.node_id}: {'+' if n.impact > 0 else ''}{n.impact*100:.0f}% "
            f"(T+{n.days_to_effect}d, {n.confidence*100:.0f}% conf)"
            for n in top_impacts
        )

        # Optional weather disruption block
        weather_block = ""
        if seed.disruption:
            d = seed.disruption
            ow = d.origin_weather
            dw = d.dest_weather
            weather_block = (
                f"\nWEATHER DISRUPTION (on-time probability {d.on_time_probability*100:.0f}%):\n"
                f"  Origin {ow.airport_code}: {ow.weather_emoji} {ow.weather_desc}, "
                f"wind {ow.wind_speed_kmh:.0f} km/h, disruption score {ow.disruption_score}/100 ({ow.risk_level})\n"
                f"  Dest {dw.airport_code}: {dw.weather_emoji} {dw.weather_desc}, "
                f"wind {dw.wind_speed_kmh:.0f} km/h, disruption score {dw.disruption_score}/100 ({dw.risk_level})\n"
                f"  Primary risk: {d.primary_risk_factor}"
            )

        news_block = ""
        if news_context:
            news_lines = "\n".join(f"  - {item}" for item in news_context[:10])
            news_block = f"\n\nBREAKING NEWS CONTEXT (selected by analyst):\n{news_lines}"

        return f"""ROUTE: {seed.route_label}
MACRO SHOCK: {seed.trigger_id}
CURRENT FARE: ${seed.fare.current_price_usd:.0f} (source: {seed.fare.source})
HISTORICAL BASELINE: ${seed.history.baseline_price_usd:.0f}
DEMAND INDEX: {seed.demand.demand_index:.2f} ({seed.demand.flights_last_24h} flights/24h)
MACRO: VIX={seed.macro.vix}, WTI=${seed.macro.wti_price:.0f}, USD/EUR={seed.macro.usd_eur}

P&L CASCADE TOP IMPACTS:
{impact_lines}{weather_block}{news_block}"""

    def _agent_turn(
        self,
        agent: Agent,
        round_num: int,
        context: str,
        market_state: dict,
        previous_actions: list[AgentAction],
    ) -> AgentAction:
        """Ask the LLM to play one agent's turn."""

        # Summarise actions from the most recent completed round (round-based window)
        recent = [
            a for a in previous_actions
            if a.agent_id != agent.id and a.round_num >= round_num - 1
        ]
        recent_summary = "\n".join(
            f"  - {a.agent_name} ({a.agent_id}): {a.decision} "
            f"{'+' if a.magnitude >= 0 else ''}{a.magnitude*100:.0f}% — {a.reasoning[:80]}"
            for a in recent
        ) or "  (no prior moves)"

        prompt = f"""You are {agent.name}, {agent.role}.

PERSONALITY: {agent.personality}
CONSTRAINTS: {agent.constraints}
FUEL HEDGE: {agent.hedge_ratio*100:.0f}%

MARKET CONTEXT (Round {round_num}):
{context}
Current market price: ${market_state['current_price']:.0f}
LCC last move: {market_state['lcc_last_move']*100:+.0f}%
Legacy last move: {market_state['legacy_last_move']*100:+.0f}%

OTHER AGENTS' RECENT MOVES:
{recent_summary}

Respond with ONLY a JSON object. No prose, no markdown, no explanation outside the JSON.
{{"decision": "raise_fares", "magnitude": 0.12, "reasoning": "One sentence, max 120 chars.", "confidence": 0.85}}

Rules:
- decision: one of raise_fares | hold_fares | drop_fares | delay_booking | accelerate_booking | shift_carrier
- magnitude: float -0.30 to 0.30
- reasoning: ONE sentence, strictly under 120 characters
- confidence: float 0.0 to 1.0"""

        try:
            response = self.llm.chat_json(
                messages=[{"role": "user", "content": prompt}],
                temperature=Config.SIMULATION_TEMPERATURE,
                max_tokens=8192,
            )
            decision = str(response.get("decision", "hold_fares"))
            magnitude = float(response.get("magnitude", 0.0))
            magnitude = max(-0.30, min(0.30, magnitude))
            reasoning = str(response.get("reasoning", ""))[:300]
            confidence = float(response.get("confidence", 0.5))
            confidence = max(0.0, min(1.0, confidence))
        except Exception as e:
            logger.warning(f"Agent {agent.id} LLM call failed: {e}")
            decision = "hold_fares"
            magnitude = 0.0
            reasoning = "LLM unavailable — defaulting to hold."
            confidence = 0.3

        return AgentAction(
            round_num=round_num,
            agent_id=agent.id,
            agent_name=agent.name,
            decision=decision,
            magnitude=magnitude,
            reasoning=reasoning,
            confidence=confidence,
        )

    def _extract_prediction(
        self,
        actions: list[AgentAction],
        cascade: dict[str, NodeImpact],
    ) -> tuple[float, float, int]:
        """
        Derive fare delta, confidence, and days_to_effect from agent actions.
        Airline agents (lcc_rm, legacy_rm) drive the price; buyer agents reflect demand.
        """
        # Revenue-side agents weighted by market share
        pricer_agents = {a.id: a for a in AIRLINE_AGENTS if a.market_share > 0}
        total_weight = sum(a.market_share for a in pricer_agents.values())

        weighted_delta = 0.0
        weighted_conf = 0.0

        for agent in pricer_agents.values():
            agent_actions = [a for a in actions if a.agent_id == agent.id]
            if not agent_actions:
                continue
            # Take the last round's action as the settled position
            last = agent_actions[-1]
            w = agent.market_share / total_weight
            weighted_delta += last.magnitude * w
            weighted_conf += last.confidence * w

        # Blend with cascade YIELD_MGT signal
        yield_impact = cascade.get("YIELD_MGT")
        if yield_impact:
            # 60% agent simulation, 40% cascade model
            weighted_delta = weighted_delta * 0.6 + yield_impact.impact * 0.4
            weighted_conf = (weighted_conf + yield_impact.confidence) / 2

        days = cascade.get("YIELD_MGT", cascade.get("RASK", None))
        days_to_effect = days.days_to_effect if days else 10

        return round(weighted_delta, 4), round(weighted_conf, 2), days_to_effect

    def _consensus_label(self, delta: float, confidence: float) -> str:
        if delta > 0.10:
            return "strong_raise"
        if delta > 0.04:
            return "moderate_raise"
        if delta < -0.10:
            return "strong_drop"
        if delta < -0.04:
            return "moderate_drop"
        return "hold"

    def _generate_report(
        self,
        seed: LiveSeed,
        cascade: dict[str, NodeImpact],
        actions: list[AgentAction],
        fare_delta: float,
        confidence: float,
    ) -> str:
        """Generate a 4-section intelligence report using the LLM."""

        # Summarise key agent positions (last round)
        agent_summary = "\n".join(
            f"- {a.agent_name} ({a.agent_id}): {a.decision} "
            f"{'+' if a.magnitude >= 0 else ''}{a.magnitude*100:.0f}% — {a.reasoning}"
            for a in actions
            if a.round_num == max(x.round_num for x in actions)
        )

        top_nodes = sorted(cascade.values(), key=lambda x: abs(x.impact), reverse=True)[:4]
        cascade_lines = "\n".join(
            f"  {n.node_id}: {'+' if n.impact > 0 else ''}{n.impact*100:.0f}% "
            f"({n.mechanism[:60]})"
            for n in top_nodes
        )

        # Pull extra context for richer, route-specific analysis
        airline  = seed.fare.airline_name or "unknown carrier"
        macro_ctx = (
            f"VIX {seed.macro.vix:.1f} ({'elevated' if seed.macro.vix > 25 else 'normal'}), "
            f"WTI ${seed.macro.wti_price:.0f}/bbl, "
            f"USD/EUR {seed.macro.usd_eur:.3f}"
        )
        wx_ctx = ""
        if seed.disruption:
            wx_ctx = (
                f"Origin weather: {seed.disruption.origin_weather.weather_desc} "
                f"(disruption score {seed.disruption.origin_weather.disruption_score}/100). "
                f"Dest weather: {seed.disruption.dest_weather.weather_desc} "
                f"(disruption score {seed.disruption.dest_weather.disruption_score}/100). "
                f"On-time probability: {seed.disruption.on_time_probability*100:.0f}%."
            )
        demand_ctx = (
            f"Demand index {seed.demand.demand_index:.2f} "
            f"({seed.demand.flights_last_24h} flights in last 24h on this route)"
        )
        history_ctx = (
            f"Historical baseline ${seed.history.baseline_price_usd:.0f}, "
            f"trend {seed.history.price_trend*100:+.1f}% vs monthly avg"
        )

        prompt = f"""You are a senior airline revenue intelligence analyst writing a confidential fare outlook brief for a corporate travel manager.

ROUTE: {seed.route_label}
SHOCK EVENT: {seed.trigger_id}
CURRENT FARE: ${seed.fare.current_price_usd:.0f} ({airline}, source: {seed.fare.source})
PREDICTED DELTA: {fare_delta*100:+.1f}% → implied ${seed.fare.current_price_usd * (1 + fare_delta):.0f}
MODEL CONFIDENCE: {confidence*100:.0f}%
MACRO: {macro_ctx}
DEMAND: {demand_ctx}
HISTORY: {history_ctx}
{f"WEATHER/OPS: {wx_ctx}" if wx_ctx else ""}

AGENT FINAL POSITIONS (last simulation round):
{agent_summary}

TOP CASCADE IMPACTS:
{cascade_lines}

Write a sharp 4-section analysis. Use the actual numbers above — do not be vague about prices or percentages.
Each section is 2–3 sentences of substance. No filler, no repetition of headings in body text.
Vary sentence structure. Write like an analyst, not a template.

## What Happened
## How Airlines Will Respond
## What This Means for Fares
## Watch List"""

        try:
            narrative = self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=8192,
            )
        except Exception as e:
            logger.warning(f"Report generation failed: {e}")
            narrative = (
                f"## What Happened\n"
                f"A {seed.trigger_id} shock was applied to the {seed.route_label} route.\n\n"
                f"## How Airlines Will Respond\n"
                f"Agent simulation indicates a consensus of "
                f"{'fare increases' if fare_delta > 0 else 'fare holds or drops'}.\n\n"
                f"## What This Means for Fares\n"
                f"Predicted fare delta: {fare_delta*100:+.1f}% with {confidence*100:.0f}% confidence.\n\n"
                f"## Watch List\n"
                f"1. Load factor on route  2. LCC pricing moves  3. Fuel spot price"
            )

        return narrative
