"""Unit tests for the deterministic analytics tools (no LLM, no network)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from copilot.schemas import run_tool
from copilot.tools import inventory, price_trends, weather_risk


def test_storm_summary_structure():
    out = weather_risk.storm_risk_summary()
    assert out["threshold_critical_ms"] == 21.0
    assert len(out["stations"]) == 3
    for st in out["stations"]:
        assert st["days_observed"] > 30
        assert 0 < st["max_gust_ms"] < 60
        assert st["days_over_critical"] <= st["days_over_caution"]


def test_recent_gusts_and_unknown_station():
    out = weather_risk.recent_gusts("Växjö", days=7)
    assert out["station"] == "Växjö A"
    assert len(out["series"]) == 7
    assert "error" in weather_risk.recent_gusts("Stockholm")


def test_price_summary_real_ranges():
    out = price_trends.price_summary("Sawlogs", "Götaland")
    assert out["assortment"] == "Sawlogs"
    # Sanity bounds from the official series (2019-): prices are in SEK/m3.
    assert 400 < out["min_since_2019"] < out["max_since_2019"] < 2000
    assert out["quarters_covered"] >= 28


def test_price_summary_unknown_returns_options():
    out = price_trends.price_summary("Bananas", "Götaland")
    assert "error" in out and "available_assortments" in out


def test_network_summary_balance():
    out = inventory.network_summary()
    assert out["weekly_supply_capacity_m3"] > out["weekly_demand_m3"]
    assert 0 < out["harvest_supply_hhi"] < 1
    assert len(out["nodes"]) == 8


def test_whatif_no_disruption_no_stockout():
    out = inventory.stockout_whatif(supply_reduction_pct=0, duration_weeks=12)
    assert out["total_unmet_demand_m3"] == 0
    assert out["fill_rate_pct"] == 100.0
    assert all(n["weeks_to_stockout"] is None for n in out["nodes"])


def test_whatif_severe_disruption_causes_stockout():
    out = inventory.stockout_whatif(supply_reduction_pct=60, duration_weeks=8)
    assert out["total_unmet_demand_m3"] > 0
    assert out["fill_rate_pct"] < 100.0
    breached = [n for n in out["nodes"] if n["weeks_to_stockout"] is not None]
    assert breached, "60% cut over 8 weeks must stock out at least one node"
    for n in out["nodes"]:
        if n["weeks_to_stockout"] is not None:
            assert n["weeks_to_safety_stock_breach"] <= n["weeks_to_stockout"]


def test_whatif_monotonic_in_severity():
    mild = inventory.stockout_whatif(20, 8)["total_unmet_demand_m3"]
    severe = inventory.stockout_whatif(70, 8)["total_unmet_demand_m3"]
    assert severe >= mild


def test_whatif_input_validation():
    assert "error" in inventory.stockout_whatif(150, 8)
    assert "error" in inventory.stockout_whatif(20, 0)


def test_dispatch_layer():
    out = run_tool("price_summary", {"assortment": "Pulpwood total"})
    assert "latest_price_sek_m3" in out
    assert "error" in run_tool("nonexistent_tool", {})
    assert "error" in run_tool("stockout_whatif", {"bogus_arg": 1})


def test_risk_snapshot_combines_all_sources():
    out = run_tool("risk_snapshot", {})
    assert set(out) == {"weather", "prices", "network"}
