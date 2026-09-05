"""Provenance manifest for raw data files (SHA-256 + retrieval metadata)."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

MANIFEST = Path(__file__).resolve().parents[1] / "data" / "raw" / "manifest.json"


def update_manifest(path: Path, source: str, url: str, license: str) -> None:
    entries = {}
    if MANIFEST.exists():
        entries = json.loads(MANIFEST.read_text())
    entries[path.name] = {
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bytes": path.stat().st_size,
        "retrieved_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": source,
        "url": url,
        "license": license,
    }
    MANIFEST.write_text(json.dumps(entries, indent=2, ensure_ascii=False))
