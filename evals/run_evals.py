"""Eval harness for the LLM agent.

Runs the golden questions against the live agent (requires ANTHROPIC_API_KEY)
and checks two things per case:

1. Tool routing — the agent called one of the expected tools (or none, for the
   honesty case).
2. Numeric grounding — every number stated in the final answer also appears
   somewhere in the tool outputs of that conversation. This operationalises the
   "no invented numbers" rule.

Usage:  PYTHONPATH=src python evals/run_evals.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from copilot.agent import ask

CASES = json.loads((Path(__file__).parent / "golden_questions.json").read_text())["cases"]

# Numbers worth grounding: >= 2 significant digits (skip "3 weeks" style small ints
# only when they also appear in tool output — small ints are checked too, but
# 1-digit years/counts rarely false-positive).
NUM_RE = re.compile(r"\d+(?:[.,]\d+)?")
FORECAST_MARKERS = ["cannot", "can't", "not able", "no forecast", "doesn't", "does not", "won't", "unable", "historical"]


def numbers_in(text: str) -> set[str]:
    return {m.replace(",", "").rstrip(".") for m in NUM_RE.findall(text)}


def main() -> None:
    passed = 0
    for case in CASES:
        result = ask(case["question"])
        tools_called = {c["tool"] for c in result.tool_calls}
        ok, notes = True, []

        if case["expected_tools"]:
            if not tools_called & set(case["expected_tools"]):
                ok, notes = False, [f"expected one of {case['expected_tools']}, got {sorted(tools_called)}"]

        if case.get("must_not_forecast"):
            if not any(m in result.text.lower() for m in FORECAST_MARKERS):
                ok = False
                notes.append("expected a refusal/limitation statement for out-of-scope forecast")

        # Grounding: every number in the answer must appear in some tool output.
        tool_blob = json.dumps([c["output"] for c in result.tool_calls])
        tool_numbers = numbers_in(tool_blob)
        ungrounded = {
            n for n in numbers_in(result.text)
            if n not in tool_numbers and n not in {"2019", "2028", "15", "21"}  # thresholds/years named in prompts
        }
        if case["expected_tools"] and ungrounded:
            ok = False
            notes.append(f"ungrounded numbers in answer: {sorted(ungrounded)}")

        status = "PASS" if ok else "FAIL"
        passed += ok
        print(f"[{status}] {case['id']}: tools={sorted(tools_called)}" + (f" — {'; '.join(notes)}" if notes else ""))

    print(f"\n{passed}/{len(CASES)} cases passed")
    sys.exit(0 if passed == len(CASES) else 1)


if __name__ == "__main__":
    main()
