"""
AirWave Cascade Engine
BFS propagation through airline P&L nodes.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple, Union


# ── Node definitions ──────────────────────────────────────────────────────────

NODE_IDS = [
    "PASSENGER_DEMAND", "LOAD_FACTOR", "YIELD_MGT", "ANCILLARY",
    "CARGO", "FUEL_COST", "LABOR_COST", "DISTRIBUTION",
    "RASK", "CASK", "OPERATING_MARGIN", "NETWORK_EFFECTS",
]

# Plain-English labels and explanations (shown in UI instead of technical jargon)
NODE_PLAIN: Dict[str, Dict[str, str]] = {
    "PASSENGER_DEMAND": {
        "label": "Traveler Demand",
        "icon": "👥",
        "what": "How many people are actively searching and booking this route.",
        "why": "When bookings dry up, airlines drop prices to fill seats. When demand surges, fares spike fast.",
    },
    "LOAD_FACTOR": {
        "label": "Seat Occupancy",
        "icon": "💺",
        "what": "The percentage of seats actually filled on each flight.",
        "why": "Airlines target 85%+ occupancy. Below that, expect discounting. Above it, expect price jumps.",
    },
    "YIELD_MGT": {
        "label": "Smart Pricing",
        "icon": "📊",
        "what": "The automated systems that re-price seats thousands of times per day.",
        "why": "When the algorithm detects a demand or cost signal, it opens or closes fare buckets within hours.",
    },
    "ANCILLARY": {
        "label": "Add-on Revenue",
        "icon": "🧳",
        "what": "Fees from checked bags, seat upgrades, priority boarding, and in-flight purchases.",
        "why": "Budget carriers earn 40–50% of revenue from add-ons. This can buffer changes to the base fare.",
    },
    "CARGO": {
        "label": "Cargo Revenue",
        "icon": "📦",
        "what": "Money earned shipping freight in the aircraft belly alongside passenger bags.",
        "why": "Long-haul airlines earn 10–20% from cargo. A cargo uptick can let airlines hold passenger fares steady.",
    },
    "FUEL_COST": {
        "label": "Fuel Bills",
        "icon": "⛽",
        "what": "Jet fuel — the single biggest operating cost for any airline.",
        "why": "Fuel is 25–35% of total costs. A 10% fuel spike usually pushes fares up within days.",
    },
    "LABOR_COST": {
        "label": "Staff Costs",
        "icon": "👷",
        "what": "Wages for pilots, cabin crew, and ground staff.",
        "why": "During disruptions, overtime, rebooking agents, and crew rescheduling pile on extra costs quickly.",
    },
    "DISTRIBUTION": {
        "label": "Booking Fees",
        "icon": "💻",
        "what": "What airlines pay travel sites (Expedia, Kayak) and agents per ticket sold.",
        "why": "Each booking through a major OTA can cost airlines $10–25. Volume changes affect this meaningfully.",
    },
    "RASK": {
        "label": "Revenue Per Seat",
        "icon": "💰",
        "what": "Total revenue earned divided by all available seats — the top-line efficiency metric.",
        "why": "Higher fares + full planes = higher RASK = a healthier, more profitable airline.",
    },
    "CASK": {
        "label": "Cost Per Seat",
        "icon": "📉",
        "what": "Total operating costs divided by all available seats — the cost-side efficiency metric.",
        "why": "Airlines need RASK > CASK to make money. Rising costs squeeze this gap and pressure fares upward.",
    },
    "OPERATING_MARGIN": {
        "label": "Profit Margin",
        "icon": "📈",
        "what": "How much profit remains after all operating costs are paid.",
        "why": "Airlines typically run 2–5% margins — razor thin. A small shock can flip a route from profit to loss.",
    },
    "NETWORK_EFFECTS": {
        "label": "Route Network",
        "icon": "✈️",
        "what": "How fare changes on this route affect connected flights and hub traffic.",
        "why": "Hub airports amplify shocks. One disrupted route can cascade across dozens of connecting flights.",
    },
}

# Plain-English summaries for each trigger type
TRIGGER_EXPLAIN: Dict[str, str] = {
    "FUEL_SPIKE": "Jet fuel costs jumped sharply — airlines' single biggest expense just got more expensive. Expect fare increases within days as carriers try to protect their margins.",
    "DEMAND_COLLAPSE": "Travelers are cancelling and avoiding bookings. Airlines have too many empty seats to fill, so prices will fall to attract buyers.",
    "CAPACITY_DUMP": "Too many flights were added on this route. With more seats than passengers, airlines are forced to compete on price — fares drop.",
    "ROUTE_CANCELLATION": "Some flights on this route are being cut. Fewer options means passengers have less choice — remaining fares typically rise.",
    "EXCHANGE_RATE": "A currency moved sharply. Since fuel and aircraft leases are priced in USD, airlines in affected markets adjust fares to compensate.",
    "DISRUPTION_EVENT": "A major operational event hit the network — disrupted schedules, emergency rebooking, and overtime costs spike all at once, pushing fares up.",
    "NEWS_FEED": "Breaking news from the route's geography — political instability, natural disasters, or major local events are suppressing traveller confidence. Selected headlines are fed directly into the agent simulation as context.",
}

# Edges: (from_node, to_node, base_weight)
EDGES: List[Tuple[str, str, float]] = [
    ("PASSENGER_DEMAND", "LOAD_FACTOR",      0.85),
    ("PASSENGER_DEMAND", "YIELD_MGT",        0.75),
    ("PASSENGER_DEMAND", "ANCILLARY",        0.65),
    ("LOAD_FACTOR",      "YIELD_MGT",        0.80),
    ("LOAD_FACTOR",      "RASK",             0.90),
    ("YIELD_MGT",        "RASK",             0.85),
    ("ANCILLARY",        "RASK",             0.60),
    ("CARGO",            "RASK",             0.50),
    ("FUEL_COST",        "CASK",             0.90),
    ("LABOR_COST",       "CASK",             0.70),
    ("DISTRIBUTION",     "CASK",             0.45),
    ("FUEL_COST",        "YIELD_MGT",        0.55),
    ("RASK",             "OPERATING_MARGIN", 1.0),
    ("CASK",             "OPERATING_MARGIN", -1.0),
    ("OPERATING_MARGIN", "NETWORK_EFFECTS",  0.70),
]

# Trigger seeds: impact on initial P&L nodes
TRIGGER_SEEDS: Dict[str, Dict[str, float]] = {
    "FUEL_SPIKE": {
        "FUEL_COST": 0.22,
        "PASSENGER_DEMAND": -0.06,
    },
    "DEMAND_COLLAPSE": {
        "PASSENGER_DEMAND": -0.35,
        "LOAD_FACTOR": -0.20,
    },
    "CAPACITY_DUMP": {
        "LOAD_FACTOR": 0.18,
        "YIELD_MGT": -0.15,
    },
    "ROUTE_CANCELLATION": {
        "PASSENGER_DEMAND": -0.12,
        "NETWORK_EFFECTS": -0.22,
        "DISTRIBUTION": 0.08,
    },
    "EXCHANGE_RATE": {
        "FUEL_COST": 0.14,
        "DISTRIBUTION": 0.09,
        "PASSENGER_DEMAND": -0.08,
    },
    "DISRUPTION_EVENT": {
        "PASSENGER_DEMAND": -0.18,
        "LABOR_COST": 0.15,
        "DISTRIBUTION": 0.12,
        "LOAD_FACTOR": -0.12,
    },
    "NEWS_FEED": {
        "PASSENGER_DEMAND": -0.25,
        "LOAD_FACTOR": -0.14,
        "LABOR_COST": 0.08,
        "DISTRIBUTION": 0.07,
    },
}

DECAY = 0.72
MAX_HOPS = 4


@dataclass
class NodeImpact:
    node_id: str
    impact: float          # positive = cost/price up; negative = drop
    confidence: float      # 0–1
    days_to_effect: int
    mechanism: str         # technical description (used in LLM context)
    recovery: str          # technical recovery timeline
    plain_label: str = ""  # human-readable name
    plain_what: str = ""   # what this node is
    plain_why: str = ""    # why it matters for fares


def run_cascade(trigger_id: Union[str, List[str]]) -> Dict[str, NodeImpact]:
    """
    BFS propagation from trigger seeds through the P&L graph.
    Accepts a single trigger_id string OR a list for combined shocks.
    Returns impact on every reachable node.
    """
    # Normalise to list
    if isinstance(trigger_id, str):
        trigger_ids = [trigger_id]
    else:
        trigger_ids = list(trigger_id)

    # Merge seeds from all triggers (additive, clamped to prevent runaway)
    merged_seeds: Dict[str, float] = {}
    for tid in trigger_ids:
        for node, impact in TRIGGER_SEEDS.get(tid, {}).items():
            merged_seeds[node] = merged_seeds.get(node, 0.0) + impact
    for node in merged_seeds:
        merged_seeds[node] = max(-0.85, min(0.85, merged_seeds[node]))

    if not merged_seeds:
        return {}

    # Build adjacency: node → [(target, weight)]
    adj: Dict[str, List[Tuple[str, float]]] = {n: [] for n in NODE_IDS}
    for src, tgt, w in EDGES:
        adj[src].append((tgt, w))

    impacts: Dict[str, float] = {}
    hops: Dict[str, int] = {}

    queue: List[Tuple[str, float, int]] = []
    for node, seed_impact in merged_seeds.items():
        impacts[node] = seed_impact
        hops[node] = 0
        queue.append((node, seed_impact, 0))

    visited_edges: set = set()

    i = 0
    while i < len(queue):
        current, current_impact, depth = queue[i]
        i += 1

        if depth >= MAX_HOPS:
            continue

        for target, weight in adj.get(current, []):
            edge_key = (current, target, depth)
            if edge_key in visited_edges:
                continue
            visited_edges.add(edge_key)

            propagated = current_impact * weight * (DECAY ** depth)

            if target == "OPERATING_MARGIN":
                continue

            if target in impacts:
                if abs(propagated) > abs(impacts[target]):
                    impacts[target] = propagated
                    hops[target] = depth + 1
                    queue.append((target, propagated, depth + 1))
            else:
                impacts[target] = propagated
                hops[target] = depth + 1
                queue.append((target, propagated, depth + 1))

    # Compute OPERATING_MARGIN from RASK - CASK
    rask = impacts.get("RASK", 0.0)
    cask = impacts.get("CASK", 0.0)
    impacts["OPERATING_MARGIN"] = rask - cask
    hops["OPERATING_MARGIN"] = max(hops.get("RASK", 0), hops.get("CASK", 0)) + 1

    result: Dict[str, NodeImpact] = {}
    for node_id, impact in impacts.items():
        if abs(impact) < 0.01:
            continue
        depth = hops.get(node_id, 1)
        plain = NODE_PLAIN.get(node_id, {})
        result[node_id] = NodeImpact(
            node_id=node_id,
            impact=round(impact, 4),
            confidence=round(max(0.3, 0.92 - depth * 0.12), 2),
            days_to_effect=_days_to_effect(node_id, depth),
            mechanism=_mechanism(node_id, trigger_id if isinstance(trigger_id, str) else trigger_ids[0]),
            recovery=_recovery(node_id),
            plain_label=plain.get("label", node_id.replace("_", " ").title()),
            plain_what=plain.get("what", ""),
            plain_why=plain.get("why", ""),
        )

    return result


def _days_to_effect(node_id: str, depth: int) -> int:
    base = {
        "FUEL_COST": 1, "LABOR_COST": 3, "DISTRIBUTION": 5,
        "PASSENGER_DEMAND": 2, "LOAD_FACTOR": 4, "YIELD_MGT": 5,
        "ANCILLARY": 7, "CARGO": 10, "RASK": 7, "CASK": 5,
        "OPERATING_MARGIN": 14, "NETWORK_EFFECTS": 21,
    }
    return base.get(node_id, 7) + depth * 2


def _mechanism(node_id: str, trigger_id: str) -> str:
    table: Dict[str, str] = {
        "FUEL_COST": "Spot and futures prices adjust within 24–48h; hedged carriers lag by hedge book duration",
        "PASSENGER_DEMAND": "Booking velocity drops; GDS booking curves flatten within days of shock",
        "LOAD_FACTOR": "Unsold capacity widens; yield management systems open lower booking classes",
        "YIELD_MGT": "RM systems detect demand signal shift; automated class opens/closes fire",
        "ANCILLARY": "Ancillary attach rates correlate with base fare level and booking confidence",
        "CARGO": "Cargo yield follows belly capacity availability and freight spot market",
        "LABOR_COST": "IRROP overtime, rebooking agent hours, crew re-rostering surge",
        "DISTRIBUTION": "GDS segment fees increase with rebooking volume; NDC insulated",
        "RASK": "Revenue per ASK is the net of yield and load factor movements",
        "CASK": "Cost per ASK moves with fuel, labour, and distribution in sequence",
        "OPERATING_MARGIN": "RASK–CASK spread; squeezed when cost shocks outrun revenue recovery",
        "NETWORK_EFFECTS": "Hub connecting traffic reacts last; feeder routes take 3–4 weeks to stabilise",
    }
    return table.get(node_id, "Indirect propagation through P&L chain")


def _recovery(node_id: str) -> str:
    table: Dict[str, str] = {
        "FUEL_COST": "Tracks commodity markets; hedge book provides 30–180d buffer",
        "PASSENGER_DEMAND": "Recovers in 4–12 weeks post-shock depending on severity",
        "LOAD_FACTOR": "Normalises once pricing stabilises; 6–10 weeks typical",
        "YIELD_MGT": "RM systems self-correct within 2–4 weeks of stabilised demand signal",
        "ANCILLARY": "Lags base demand recovery by 1–2 weeks",
        "CARGO": "Spot freight market driven; 4–8 weeks",
        "LABOR_COST": "IRROP costs subside in 2–5 days post-disruption",
        "DISTRIBUTION": "GDS fees normalise with booking volumes; 2–6 weeks",
        "RASK": "Full recovery 8–16 weeks post-shock",
        "CASK": "6–12 weeks depending on fuel hedge duration",
        "OPERATING_MARGIN": "Lags both RASK and CASK recovery; 10–20 weeks",
        "NETWORK_EFFECTS": "Slowest to recover; 4–8 weeks for connecting traffic normalisation",
    }
    return table.get(node_id, "Recovery timeline varies with shock magnitude")
