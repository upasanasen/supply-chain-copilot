"""Storm-risk analytics over real SMHI gust observations (stdlib only)."""
from __future__ import annotations

import csv
from pathlib import Path
from statistics import mean

DATA = Path(__file__).resolve().parents[3] / "data" / "processed" / "wind_daily.csv"

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

    out = {"threshold_caution_ms": CAUTION_GUST, "threshold_critical_ms": CRITICAL_GUST, "stations": []}
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
    rows = [r for r in _load() if station.lower() in r["station"].lower()]
    if not rows:
        return {"error": f"No station matching {station!r}. Available: Växjö A, Hagshult, Ljungby A."}
    rows.sort(key=lambda r: r["date"])
    tail = rows[-days:]
    return {
        "station": rows[0]["station"],
        "series": [{"date": r["date"], "max_gust_ms": r["max_gust_ms"]} for r in tail],
    }
