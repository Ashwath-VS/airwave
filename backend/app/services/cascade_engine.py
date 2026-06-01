"""
AirWave Cascade Engine
BFS propagation through airline P&L nodes.
Ported from lib/airlineData.ts in the portfolio project.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


# ── Node definitions ──────────────────────────────────────────────────────────

NODE_IDS = [
    "PASSENGER_DEMAND", "LOAD_FACTOR", "YIELD_MGT", "ANCILLARY",
    "CARGO", "FUEL_COST", "LABOR_COST", "DISTRIBUTION",
    "RASK", "CASK", "OPERATING_MARGIN", "NETWORK_EFFECTS",
]

# Edges: (from_node, to_node, base_weight)
EDGES: List[Tuple[str, str, float]] = [
    ("PASSENGER_DEMAND", "LOAD_FACTOR",     0.85),
    ("PASSENGER_DEMAND", "YIELD_MGT",       0.75),
    ("PASSENGER_DEMAND", "ANCILLARY",       0.65),
    ("LOAD_FACTOR",      "YIELD_MGT",       0.80),
    ("LOAD_FACTOR",      "RASK",            0.90),
    ("YIELD_MGT",        "RASK",            0.85),
    ("ANCILLARY",        "RASK",            0.60),
    ("CARGO",            "RASK",            0.50),
    ("FUEL_COST",        "CASK",            0.90),
    ("LABOR_COST",       "CASK",            0.70),
    ("DISTRIBUTION",     "CASK",            0.45),
    ("FUEL_COST",        "YIELD_MGT",       0.55),  # fuel shock → pricing pressure
    ("RASK",             "OPERATING_MARGIN", 1.0),
    ("CASK",             "OPERATING_MARGIN", -1.0),  # cost side inverted
    ("OPERATING_MARGIN", "NETWORK_EFFECTS", 0.70),
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
}

DECAY = 0.72
MAX_HOPS = 4


@dataclass
class NodeImpact:
    node_id: str
    impact: float          # positive = cost up / revenue contribution; negative = drop
    confidence: float      # 0–1
    days_to_effect: int
    mechanism: str
    recovery: str


def run_cascade(trigger_id: str) -> Dict[str, NodeImpact]:
    """
    BFS propagation from trigger seeds through the P&L graph.
    Returns impact on every reachable node.
    """
    seeds = TRIGGER_SEEDS.get(trigger_id, {})
    if not seeds:
        return {}

    # Build adjacency: node → [(target, weight)]
    adj: Dict[str, List[Tuple[str, float]]] = {n: [] for n in NODE_IDS}
    for src, tgt, w in EDGES:
        adj[src].append((tgt, w))

    impacts: Dict[str, float] = {}
    hops: Dict[str, int] = {}

    # Seed
    queue: List[Tuple[str, float, int]] = []
    for node, seed_impact in seeds.items():
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

            # OPERATING_MARGIN: special — difference of RASK and CASK impacts
            if target == "OPERATING_MARGIN":
                # handled after all nodes computed
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

    # Build NodeImpact objects
    result: Dict[str, NodeImpact] = {}
    for node_id, impact in impacts.items():
        if abs(impact) < 0.01:
            continue
        depth = hops.get(node_id, 1)
        result[node_id] = NodeImpact(
            node_id=node_id,
            impact=round(impact, 4),
            confidence=round(max(0.3, 0.92 - depth * 0.12), 2),
            days_to_effect=_days_to_effect(node_id, depth),
            mechanism=_mechanism(node_id, trigger_id),
            recovery=_recovery(node_id),
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
