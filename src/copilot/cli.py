"""CLI entry points.

python -m copilot.cli demo     # deterministic tool demo, no API key needed
python -m copilot.cli report   # deterministic markdown risk snapshot, no key
python -m copilot.cli chat     # interactive LLM agent (needs ANTHROPIC_API_KEY)
python -m copilot.cli ask "…"  # one-shot LLM question (needs key)
"""

from __future__ import annotations

import json
import sys

from .schemas import run_tool
from .tools import report


def cmd_demo() -> None:
    print("=== supply-chain-copilot: deterministic tool demo (no LLM) ===\n")
    calls = [
        ("storm_risk_summary", {}),
        ("price_summary", {"assortment": "Sawlogs", "region": "Götaland"}),
        ("network_summary", {}),
        ("stockout_whatif", {"supply_reduction_pct": 40, "duration_weeks": 6}),
    ]
    for name, args in calls:
        print(f"--- {name}({json.dumps(args) if args else ''}) ---")
        print(json.dumps(run_tool(name, args), indent=2, ensure_ascii=False))
        print()
    print("These are the exact tools the LLM agent calls in chat mode.")


def cmd_report() -> None:
    snap = report.risk_snapshot()
    w = snap["weather"]
    saw = snap["prices"]["sawlogs_gotaland"]
    pulp = snap["prices"]["pulpwood_gotaland"]
    net = snap["network"]

    lines = ["# Supply-chain risk snapshot\n"]
    lines.append("## Storm exposure (real SMHI observations)\n")
    for st in w["stations"]:
        lines.append(
            f"- **{st['station']}** ({st['window']}): max gust {st['max_gust_ms']} m/s "
            f"on {st['max_gust_date']}; {st['days_over_caution']} days ≥ "
            f"{w['threshold_caution_ms']} m/s, "
            f"{st['days_over_critical']} days ≥ {w['threshold_critical_ms']} m/s."
        )
    lines.append("\n## Price momentum (real Swedish Forest Agency data)\n")
    for label, p in (("Sawlogs", saw), ("Pulpwood", pulp)):
        lines.append(
            f"- **{label}, {p['region']}** ({p['latest_quarter']}): "
            f"{p['latest_price_sek_m3']} SEK/m³ "
            f"({p['qoq_change_pct']:+.1f}% QoQ, {p['yoy_change_pct']:+.1f}% YoY; "
            f"range since 2019: {p['min_since_2019']}–{p['max_since_2019']})."
        )
    lines.append("\n## Network posture (synthetic illustrative network)\n")
    lines.append(
        f"- Weekly supply capacity {net['weekly_supply_capacity_m3']:.0f} m³ vs demand "
        f"{net['weekly_demand_m3']:.0f} m³ ({net['supply_slack_pct']}% slack); "
        f"harvest concentration HHI {net['harvest_supply_hhi']}."
    )
    print("\n".join(lines))


def cmd_chat() -> None:
    from .agent import ask

    print("supply-chain-copilot chat — type a question, or 'quit'. (Ctrl-C to exit)")
    history: list[dict] = []
    while True:
        try:
            q = input("\nyou> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not q or q.lower() in {"quit", "exit"}:
            return
        result = ask(q, history=history)
        for call in result.tool_calls:
            print(f"  [tool] {call['tool']}({json.dumps(call['input'], ensure_ascii=False)})")
        print(f"\ncopilot> {result.text}")
        # Preserve assistant tool calls and their results so follow-up questions
        # retain the evidence behind earlier answers.
        history = result.messages


def cmd_ask(question: str) -> None:
    from .agent import ask

    result = ask(question)
    for call in result.tool_calls:
        print(
            f"[tool] {call['tool']}({json.dumps(call['input'], ensure_ascii=False)})",
            file=sys.stderr,
        )
    print(result.text)


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] == "demo":
        cmd_demo()
    elif args[0] == "report":
        cmd_report()
    elif args[0] == "chat":
        cmd_chat()
    elif args[0] == "ask" and len(args) > 1:
        cmd_ask(" ".join(args[1:]))
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
