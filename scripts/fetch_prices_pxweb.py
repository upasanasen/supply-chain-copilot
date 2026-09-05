"""Fetch real quarterly roundwood prices from the Swedish Forest Agency PxWeb API.

Table JO0303_3ny.px: average delivery-timber prices (SEK/m3 solid under bark)
by region and assortment, quarterly from 2019Q1.

Outputs:
  data/raw/roundwood_prices.json     (latest raw response; prior commits remain in Git)
  data/processed/prices_quarterly.csv (region, assortment, quarter, price_sek_m3)
  data/raw/manifest.json             (updated with SHA-256 + provenance)

Source: Skogsstyrelsen (Swedish Forest Agency) statistical database.
"""

from __future__ import annotations

import csv
import json
import urllib.request
from pathlib import Path

from manifest import update_manifest

URL = (
    "https://pxweb.skogsstyrelsen.se/api/v1/en/"
    "Skogsstyrelsens%20statistikdatabas/Rundvirkespriser/JO0303_3ny.px"
)

QUERY = {
    "query": [
        # All regions, all assortments, all quarters
    ],
    "response": {"format": "json"},
}

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"


def _request(url: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "User-Agent": "supply-chain-copilot (portfolio project)",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8-sig"))


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)

    meta = _request(URL)
    labels: dict[str, dict[str, str]] = {}
    for var in meta["variables"]:
        labels[var["code"]] = dict(zip(var["values"], var["valueTexts"], strict=True))

    payload = _request(URL, QUERY)
    raw_path = RAW / "roundwood_prices.json"
    raw_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    update_manifest(
        raw_path,
        source="Skogsstyrelsen PxWeb table JO0303_3ny.px (quarterly roundwood prices)",
        url=URL,
        license="Public Swedish official statistics",
    )

    out = PROCESSED / "prices_quarterly.csv"
    n = 0
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["region", "assortment", "quarter", "price_sek_m3"])
        for row in payload["data"]:
            region_code, assort_code, quarter_code = row["key"]
            value = row["values"][0]
            if value in ("..", ".", ""):
                continue
            region = labels["Landsdel"][region_code]
            assortment = labels["Sortiment"][assort_code]
            quarter = labels["Kvartal"][quarter_code]
            writer.writerow([region, assortment, quarter, value])
            n += 1
    print(f"Wrote {out} ({n} rows)")


if __name__ == "__main__":
    main()
