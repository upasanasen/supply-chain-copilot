"""Tool definitions exposed to the LLM, and the dispatch table."""

from __future__ import annotations

import csv

from .tools import inventory, price_trends, report, weather_risk

TOOLS = [
    {
        "name": "storm_risk_summary",
        "description": (
            "Per-station storm exposure from real SMHI gust observations "
            "(3 stations in the Småland forest region, ~4 recent months): max gusts, "
            "days over caution (15 m/s) and critical (21 m/s) thresholds, recent trend."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
    },
    {
        "name": "recent_gusts",
        "description": "Daily max gusts for one station over the last N observed days.",
        "input_schema": {
            "type": "object",
            "properties": {
                "station": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Station name (Växjö, Hagshult, or Ljungby)",
                },
                "days": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": weather_risk.MAX_RECENT_DAYS,
                    "description": "Number of days (default 14)",
                },
            },
            "required": ["station"],
            "additionalProperties": False,
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
                "assortment": {
                    "type": "string",
                    "minLength": 1,
                    "description": "e.g. 'Sawlogs' or 'Pulpwood total'",
                },
                "region": {"type": "string", "minLength": 1, "description": "e.g. 'Götaland'"},
            },
            "required": [],
            "additionalProperties": False,
        },
    },
    {
        "name": "price_series",
        "description": (
            "Raw quarterly price series (last N quarters) for one region and assortment."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "assortment": {"type": "string", "minLength": 1},
                "region": {"type": "string", "minLength": 1},
                "last_n": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": price_trends.MAX_SERIES_POINTS,
                    "description": "Quarters to return (default 8)",
                },
            },
            "required": [],
            "additionalProperties": False,
        },
    },
    {
        "name": "network_summary",
        "description": (
            "Structure and posture of the (synthetic, illustrative) 8-node supply network: "
            "nodes, weekly supply vs demand, slack, and harvest supply concentration (HHI)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
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
                "supply_reduction_pct": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 100,
                    "description": "0-100",
                },
                "duration_weeks": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 52,
                    "description": "1-52",
                },
            },
            "required": ["supply_reduction_pct", "duration_weeks"],
            "additionalProperties": False,
        },
    },
    {
        "name": "risk_snapshot",
        "description": (
            "One-call combined snapshot (weather + prices + network) for drafting risk reports."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
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
    tool = DISPATCH.get(name)
    if tool is None:
        return {"error": f"Unknown tool {name!r}"}
    try:
        return tool(**tool_input)
    except TypeError as e:
        return {"error": f"Bad arguments for {name}: {e}"}
    except (OSError, ValueError, KeyError, csv.Error) as e:
        return {
            "error": f"{name} could not complete because its data is unavailable or invalid: {e}"
        }
