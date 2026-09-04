"""Deterministic inventory what-if projections over the synthetic network.

The network is synthetic and illustrative (see data/synthetic/README.md); the
projection logic itself is the point: transparent, testable arithmetic the LLM
agent can call instead of guessing numbers.
"""
from __future__ import annotations

import csv
from pathlib import Path

DATA = Path(__file__).resolve().parents[3] / "data" / "synthetic" / "network.csv"

NUMERIC = ["weekly_capacity_m3", "weekly_demand_m3", "inventory_m3", "safety_stock_m3"]


def _load() -> list[dict]:
    with DATA.open() as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k in NUMERIC:
            r[k] = float(r[k])
    return rows


def network_summary() -> dict:
    """Structure, aggregate balance, and supply-concentration (HHI) of the network."""
    rows = _load()
    supply = sum(r["weekly_capacity_m3"] for r in rows if r["node_type"] == "harvest")
    demand = sum(r["weekly_demand_m3"] for r in rows)
    shares = [
        r["weekly_capacity_m3"] / supply for r in rows if r["node_type"] == "harvest" and supply
    ]
    hhi = round(sum(s * s for s in shares), 3)
    return {
        "note": "Synthetic illustrative network (no real company data).",
        "nodes": [
            {k: r[k] for k in ("node_id", "node_name", "node_type")} | {"weekly_demand_m3": r["weekly_demand_m3"], "inventory_m3": r["inventory_m3"]}
            for r in rows
        ],
        "weekly_supply_capacity_m3": supply,
        "weekly_demand_m3": demand,
        "supply_slack_pct": round((supply / demand - 1) * 100, 1) if demand else None,
        "harvest_supply_hhi": hhi,
    }


def stockout_whatif(supply_reduction_pct: float, duration_weeks: int) -> dict:
    """Project inventory positions under a supply disruption.

    Assumes demand nodes draw first from their own inventory, replenished from
    the (reduced) harvest supply allocated pro-rata to demand. Reports weeks
    until each demand node breaches safety stock and until stockout.
    """
    if not 0 <= supply_reduction_pct <= 100:
        return {"error": "supply_reduction_pct must be between 0 and 100"}
    if not 1 <= duration_weeks <= 52:
        return {"error": "duration_weeks must be between 1 and 52"}

    rows = _load()
    supply = sum(r["weekly_capacity_m3"] for r in rows if r["node_type"] == "harvest")
    reduced_supply = supply * (1 - supply_reduction_pct / 100)
    demand_nodes = [r for r in rows if r["weekly_demand_m3"] > 0]
    total_demand = sum(r["weekly_demand_m3"] for r in demand_nodes)
    # Buffer inventory at terminals is shared upstream stock; pool it pro-rata.
    terminal_stock = sum(r["inventory_m3"] for r in rows if r["node_type"] == "terminal")

    results = []
    total_unmet = 0.0
    for node in demand_nodes:
        share = node["weekly_demand_m3"] / total_demand
        weekly_inflow = reduced_supply * share
        position = node["inventory_m3"] + terminal_stock * share
        weekly_gap = node["weekly_demand_m3"] - weekly_inflow

        weeks_to_safety = None
        weeks_to_stockout = None
        unmet = 0.0
        pos = position
        for week in range(1, duration_weeks + 1):
            pos -= weekly_gap
            if weeks_to_safety is None and pos < node["safety_stock_m3"]:
                weeks_to_safety = week
            if pos < 0:
                if weeks_to_stockout is None:
                    weeks_to_stockout = week
                unmet += min(-pos, node["weekly_demand_m3"])
                pos = 0.0
        total_unmet += unmet
        results.append(
            {
                "node": node["node_name"],
                "weekly_demand_m3": node["weekly_demand_m3"],
                "starting_position_m3": round(position),
                "weekly_shortfall_m3": round(weekly_gap),
                "weeks_to_safety_stock_breach": weeks_to_safety,
                "weeks_to_stockout": weeks_to_stockout,
                "unmet_demand_m3": round(unmet),
                "end_position_m3": round(pos),
            }
        )

    return {
        "note": "Synthetic illustrative network; deterministic pro-rata projection.",
        "scenario": {
            "supply_reduction_pct": supply_reduction_pct,
            "duration_weeks": duration_weeks,
            "baseline_weekly_supply_m3": supply,
            "reduced_weekly_supply_m3": round(reduced_supply),
        },
        "nodes": results,
        "total_unmet_demand_m3": round(total_unmet),
        "fill_rate_pct": round(
            (1 - total_unmet / (total_demand * duration_weeks)) * 100, 1
        ),
    }
