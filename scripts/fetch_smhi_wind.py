"""Fetch real wind-gust observations from SMHI Open Data (metobs API).

Pulls daily max gust (parameter 21, "Byvind, max") for weather stations near a
southern-Sweden forest supply region, using the "latest-months" period
(~4 months of hourly/3-hourly observations, no API key required).

Outputs:
  data/raw/smhi_gust_<station_id>.json       (immutable raw responses)
  data/processed/wind_daily.csv              (station, date, max_gust_ms)
  data/raw/manifest.json                     (updated with SHA-256 + provenance)

Source: SMHI Open Data API, licensed under Creative Commons BY 4.0.
https://opendata.smhi.se/
"""
from __future__ import annotations

import json
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from manifest import update_manifest

BASE = "https://opendata-download-metobs.smhi.se/api/version/1.0"
PARAMETER = 21  # max gust (m/s)
# Stations chosen to bracket the Götaland / Småland forest region.
STATION_NAME_QUERIES = ["Växjö", "Hagshult", "Ljungby"]

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"


def _get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "supply-chain-copilot (portfolio project)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def find_stations() -> list[dict]:
    """Resolve station ids by name match against the live station registry."""
    registry = _get_json(f"{BASE}/parameter/{PARAMETER}.json")
    stations = []
    for query in STATION_NAME_QUERIES:
        candidates = [s for s in registry["station"] if query.lower() in s["name"].lower() and s.get("active")]
        if candidates:
            # Prefer the station with the most recent data
            best = max(candidates, key=lambda s: s.get("updated", 0))
            stations.append({"id": best["id"], "name": best["name"]})
        else:
            print(f"WARNING: no active station matching {query!r}", file=sys.stderr)
    return stations


def fetch_station(station_id: int) -> dict:
    url = f"{BASE}/parameter/{PARAMETER}/station/{station_id}/period/latest-months/data.json"
    return _get_json(url)


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)

    stations = find_stations()
    if not stations:
        sys.exit("No stations resolved; aborting.")

    daily: dict[tuple[str, str], float] = {}
    for st in stations:
        payload = fetch_station(st["id"])
        raw_path = RAW / f"smhi_gust_{st['id']}.json"
        raw_path.write_text(json.dumps(payload, ensure_ascii=False))
        update_manifest(
            raw_path,
            source="SMHI Open Data metobs API, parameter 21 (max gust), period latest-months",
            url=f"{BASE}/parameter/{PARAMETER}/station/{st['id']}/period/latest-months/data.json",
            license="CC BY 4.0",
        )
        for obs in payload.get("value") or []:
            date = datetime.fromtimestamp(obs["date"] / 1000, tz=timezone.utc).date().isoformat()
            gust = float(obs["value"])
            key = (st["name"], date)
            daily[key] = max(daily.get(key, 0.0), gust)
        print(f"Fetched {st['name']} (id {st['id']}): {len(payload.get('value') or [])} observations")

    rows = sorted(daily.items())
    out = PROCESSED / "wind_daily.csv"
    with out.open("w") as f:
        f.write("station,date,max_gust_ms\n")
        for (name, date), gust in rows:
            f.write(f"{name},{date},{gust}\n")
    print(f"Wrote {out} ({len(rows)} station-days)")


if __name__ == "__main__":
    main()
