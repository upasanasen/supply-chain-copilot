"""Tool definitions exposed to the LLM, and the dispatch table."""
from __future__ import annotations

from .tools import inventory, price_trends, report, weather_risk

TOOLS = [
    {
        "name": "storm_risk_summary",
        "description": (
            "Per-station storm exposure from real SMHI gust observations "
            "(3 stations in the Småland forest region, ~4 recent months): max gusts, "
            "days over caution (15 m/s) and critical (21 m/s) thresholds, recent trend."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "recent_gusts",
        "description": "Daily max gusts for one station over the last N observed days.",
        "input_schema": {
            "type": "object",
            "properties": {
                "station": {"type": "string", "description": "Station name (Växjö, Hagshult, or Ljungby)"},
                "days": {"type": "integer", "description": "Number of days (default 14)"},
            },
            "required": ["station"],
        },
    },
    {
        "name": "price_summary",
        "description": (
            "Latest quarterly roundwood price with QoQ/YoY change and 2019- range, from real "
            "Swedish Forest Agency data. Assortments include Sawlogs, Pulpwood total, "
            "Sawlogs of Norway spruce, etc. Regions: Götaland, Svealand, Southern Norrland, "
            "Northern Norrland, Entire country."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "assortment": {"type": "string", "description": "e.g. 'Sawlogs' or 'Pulpwood total'"},
                "region": {"type": "string", "description": "e.g. 'Götaland'"},
            },
            "required": [],
        },
    },
    {
        "name": "price_series",
        "description": "Raw quarterly price series (last N quarters) for one region and assortment.",
        "input_schema": {
            "type": "object",
            "properties": {
                "assortment": {"type": "string"},
                "region": {"type": "string"},
                "last_n": {"type": "integer", "description": "Quarters to return (default 8)"},
            },
            "required": [],
        },
    },
    {
        "name": "network_summary",
        "description": (
            "Structure and posture of the (synthetic, illustrative) 8-node supply network: "
            "nodes, weekly supply vs demand, slack, and harvest supply concentration (HHI)."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "stockout_whatif",
        "description": (
            "Deterministic what-if projection: reduce weekly harvest supply by X% for N weeks "
            "and report, per demand node, weeks until safety-stock breach and stockout, unmet "
            "demand, and network fill rate. Use this for every quantitative disruption question — "
            "never estimate these numbers yourself."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "supply_reduction_pct": {"type": "number", "description": "0-100"},
                "duration_weeks": {"type": "integer", "description": "1-52"},
            },
            "required": ["supply_reduction_pct", "duration_weeks"],
        },
    },
    {
        "name": "risk_snapshot",
        "description": "One-call combined snapshot (weather + prices + network) for drafting risk reports.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
]

DISPATCH = {
    "storm_risk_summary": lambda **kw: weather_risk.storm_risk_summary(),
    "recent_gusts": lambda **kw: weather_risk.recent_gusts(**kw),
    "price_summary": lambda **kw: price_trends.price_summary(**kw),
    "price_series": lambda **kw: price_trends.price_series(**kw),
    "network_summary": lambda **kw: inventory.network_summary(),
    "stockout_whatif": lambda **kw: inventory.stockout_whatif(**kw),
    "risk_snapshot": lambda **kw: report.risk_snapshot(),
}


def run_tool(name: str, tool_input: dict) -> dict:
    try:
        return DISPATCH[name](**tool_input)
    except KeyError:
        return {"error": f"Unknown tool {name!r}"}
    except TypeError as e:
        return {"error": f"Bad arguments for {name}: {e}"}
