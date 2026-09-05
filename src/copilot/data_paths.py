"""Resolve bundled datasets in a source checkout or an installed package."""

from __future__ import annotations

import sysconfig
from pathlib import Path

SOURCE_DATA = Path(__file__).resolve().parents[2] / "data"
INSTALLED_DATA = Path(sysconfig.get_path("data")) / "share" / "supply-chain-copilot" / "data"


def data_file(*parts: str) -> Path:
    """Return a data path, preferring the source checkout when available."""
    source_path = SOURCE_DATA.joinpath(*parts)
    if source_path.is_file():
        return source_path
    return INSTALLED_DATA.joinpath(*parts)
