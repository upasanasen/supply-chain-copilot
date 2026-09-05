"""Price-trend analytics over real Swedish Forest Agency roundwood prices."""

from __future__ import annotations

import csv

from ..data_paths import data_file

DATA = data_file("processed", "prices_quarterly.csv")
MAX_SERIES_POINTS = 40


def _load() -> list[dict]:
    with DATA.open() as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["price_sek_m3"] = float(r["price_sek_m3"])
    return rows


def _resolve_name(query: str, choices: set[str], label: str) -> tuple[str | None, dict | None]:
    if not isinstance(query, str) or not query.strip():
        return None, {
            "error": f"{label} must be a non-empty name",
            f"available_{label}s": sorted(choices),
        }

    normalized = query.strip().casefold()
    exact = [choice for choice in choices if choice.casefold() == normalized]
    if exact:
        return exact[0], None

    partial = [choice for choice in choices if normalized in choice.casefold()]
    if len(partial) == 1:
        return partial[0], None

    message = "No" if not partial else "Ambiguous"
    return None, {
        "error": f"{message} {label} matching {query!r}",
        f"available_{label}s": sorted(choices),
    }


def _select(rows: list[dict], region: str, assortment: str) -> tuple[list[dict], dict | None]:
    region_name, error = _resolve_name(region, {r["region"] for r in rows}, "region")
    if error:
        return [], error
    assortment_name, error = _resolve_name(
        assortment, {r["assortment"] for r in rows}, "assortment"
    )
    if error:
        return [], error

    selected = [
        r for r in rows if r["region"] == region_name and r["assortment"] == assortment_name
    ]
    selected.sort(key=lambda r: r["quarter"])
    return selected, None


def price_summary(assortment: str = "Sawlogs", region: str = "Götaland") -> dict:
    """Latest price, quarter-over-quarter and year-over-year change, range."""
    series, error = _select(_load(), region, assortment)
    if error:
        return error
    latest = series[-1]
    prev = series[-2] if len(series) >= 2 else None
    yoy = series[-5] if len(series) >= 5 else None
    prices = [r["price_sek_m3"] for r in series]
    return {
        "region": latest["region"],
        "assortment": latest["assortment"],
        "latest_quarter": latest["quarter"],
        "latest_price_sek_m3": latest["price_sek_m3"],
        "qoq_change_pct": round((latest["price_sek_m3"] / prev["price_sek_m3"] - 1) * 100, 1)
        if prev
        else None,
        "yoy_change_pct": round((latest["price_sek_m3"] / yoy["price_sek_m3"] - 1) * 100, 1)
        if yoy
        else None,
        "min_since_2019": min(prices),
        "max_since_2019": max(prices),
        "quarters_covered": len(series),
    }


def price_series(assortment: str = "Sawlogs", region: str = "Götaland", last_n: int = 8) -> dict:
    """Raw quarterly series (last N quarters) for charting or inspection."""
    if (
        isinstance(last_n, bool)
        or not isinstance(last_n, int)
        or not 1 <= last_n <= MAX_SERIES_POINTS
    ):
        return {"error": f"last_n must be an integer between 1 and {MAX_SERIES_POINTS}"}

    rows, error = _select(_load(), region, assortment)
    if error:
        return error
    series = rows[-last_n:]
    return {
        "region": series[0]["region"],
        "assortment": series[0]["assortment"],
        "series": [{"quarter": r["quarter"], "price_sek_m3": r["price_sek_m3"]} for r in series],
    }
