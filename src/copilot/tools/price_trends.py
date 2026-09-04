"""Price-trend analytics over real Swedish Forest Agency roundwood prices."""
from __future__ import annotations

import csv
from pathlib import Path

DATA = Path(__file__).resolve().parents[3] / "data" / "processed" / "prices_quarterly.csv"


def _load() -> list[dict]:
    with DATA.open() as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["price_sek_m3"] = float(r["price_sek_m3"])
    return rows


def _match(rows: list[dict], region: str, assortment: str) -> list[dict]:
    sel = [
        r
        for r in rows
        if region.lower() in r["region"].lower() and assortment.lower() in r["assortment"].lower()
    ]
    sel.sort(key=lambda r: r["quarter"])
    return sel


def price_summary(assortment: str = "Sawlogs", region: str = "Götaland") -> dict:
    """Latest price, quarter-over-quarter and year-over-year change, range."""
    rows = _match(_load(), region, assortment)
    if not rows:
        return {
            "error": f"No series for region~{region!r}, assortment~{assortment!r}.",
            "available_assortments": sorted({r["assortment"] for r in _load()}),
            "available_regions": sorted({r["region"] for r in _load()}),
        }
    # Exact-assortment disambiguation: prefer shortest matching name (e.g. "Sawlogs"
    # over "Sawlogs of Scots pine") so summaries use the aggregate series.
    best_name = min({r["assortment"] for r in rows}, key=len)
    series = [r for r in rows if r["assortment"] == best_name]
    latest = series[-1]
    prev = series[-2] if len(series) >= 2 else None
    yoy = series[-5] if len(series) >= 5 else None
    prices = [r["price_sek_m3"] for r in series]
    return {
        "region": latest["region"],
        "assortment": best_name,
        "latest_quarter": latest["quarter"],
        "latest_price_sek_m3": latest["price_sek_m3"],
        "qoq_change_pct": round((latest["price_sek_m3"] / prev["price_sek_m3"] - 1) * 100, 1) if prev else None,
        "yoy_change_pct": round((latest["price_sek_m3"] / yoy["price_sek_m3"] - 1) * 100, 1) if yoy else None,
        "min_since_2019": min(prices),
        "max_since_2019": max(prices),
        "quarters_covered": len(series),
    }


def price_series(assortment: str = "Sawlogs", region: str = "Götaland", last_n: int = 8) -> dict:
    """Raw quarterly series (last N quarters) for charting or inspection."""
    rows = _match(_load(), region, assortment)
    if not rows:
        return {"error": f"No series for region~{region!r}, assortment~{assortment!r}."}
    best_name = min({r["assortment"] for r in rows}, key=len)
    series = [r for r in rows if r["assortment"] == best_name][-last_n:]
    return {
        "region": series[0]["region"],
        "assortment": best_name,
        "series": [{"quarter": r["quarter"], "price_sek_m3": r["price_sek_m3"]} for r in series],
    }
