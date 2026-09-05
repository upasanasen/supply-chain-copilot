"""Combined risk snapshot: one call that gathers all signal sources."""

from __future__ import annotations

from . import inventory, price_trends, weather_risk


def risk_snapshot() -> dict:
    """Weather exposure + price momentum + network posture in one structure.

    Used by the agent to draft risk reports, and by the CLI's deterministic
    `report` command.
    """
    return {
        "weather": weather_risk.storm_risk_summary(),
        "prices": {
            "sawlogs_gotaland": price_trends.price_summary("Sawlogs", "Götaland"),
            "pulpwood_gotaland": price_trends.price_summary("Pulpwood total", "Götaland"),
        },
        "network": inventory.network_summary(),
    }
