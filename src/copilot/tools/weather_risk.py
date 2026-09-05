"""Storm-risk analytics over real SMHI gust observations (stdlib only)."""

from __future__ import annotations

import csv
from statistics import mean

from ..data_paths import data_file

DATA = data_file("processed", "wind_daily.csv")
MAX_RECENT_DAYS = 90

# Operational thresholds (m/s). 21 m/s gusts ≈ level where harvesting and
# forwarding are typically suspended and windthrow risk becomes material.
CAUTION_GUST = 15.0
CRITICAL_GUST = 21.0


def _load() -> list[dict]:
    with DATA.open() as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["max_gust_ms"] = float(r["max_gust_ms"])
    return rows


def storm_risk_summary() -> dict:
    """Per-station storm exposure over the observed window."""
    rows = _load()
    stations: dict[str, list[dict]] = {}
    for r in rows:
        stations.setdefault(r["station"], []).append(r)

    out = {
        "threshold_caution_ms": CAUTION_GUST,
        "threshold_critical_ms": CRITICAL_GUST,
        "stations": [],
    }
    for name, obs in sorted(stations.items()):
        obs.sort(key=lambda r: r["date"])
        gusts = [r["max_gust_ms"] for r in obs]
        recent = gusts[-14:]
        out["stations"].append(
            {
                "station": name,
                "window": f"{obs[0]['date']} to {obs[-1]['date']}",
                "days_observed": len(obs),
                "max_gust_ms": max(gusts),
                "max_gust_date": max(obs, key=lambda r: r["max_gust_ms"])["date"],
                "days_over_caution": sum(g >= CAUTION_GUST for g in gusts),
                "days_over_critical": sum(g >= CRITICAL_GUST for g in gusts),
                "mean_gust_last_14d": round(mean(recent), 1),
                "max_gust_last_14d": max(recent),
            }
        )
    return out


def recent_gusts(station: str, days: int = 14) -> dict:
    """Daily max gusts for one station over the last N observed days."""
    if not isinstance(station, str) or not station.strip():
        return {"error": "station must be a non-empty name"}
    if isinstance(days, bool) or not isinstance(days, int) or not 1 <= days <= MAX_RECENT_DAYS:
        return {"error": f"days must be an integer between 1 and {MAX_RECENT_DAYS}"}

    all_rows = _load()
    available = sorted({r["station"] for r in all_rows})
    query = station.strip().casefold()
    matches = [
        name for name in available if query in {name.casefold(), name.removesuffix(" A").casefold()}
    ]
    if len(matches) != 1:
        return {
            "error": f"No unique station matching {station!r}.",
            "available_stations": available,
        }

    selected = matches[0]
    rows = [r for r in all_rows if r["station"] == selected]
    rows.sort(key=lambda r: r["date"])
    tail = rows[-days:]
    return {
        "station": selected,
        "series": [{"date": r["date"], "max_gust_ms": r["max_gust_ms"]} for r in tail],
    }
