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
from decimal import Decimal, InvalidOperation
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from copilot.agent import ask

CASES = json.loads((Path(__file__).parent / "golden_questions.json").read_text())["cases"]

# Capture signed decimals and comma-grouped thousands while ignoring digits
# embedded in identifiers such as `m3`.
NUM_RE = re.compile(r"(?<![\w.])-?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?![\w.])")
FORECAST_MARKERS = [
    "cannot",
    "can't",
    "not able",
    "no forecast",
    "doesn't",
    "does not",
    "won't",
    "unable",
    "historical",
]


def numbers_in(text: str) -> set[str]:
    normalized = set()
    for match in NUM_RE.findall(text):
        try:
            value = Decimal(match.replace(",", ""))
        except InvalidOperation:
            continue
        normalized.add(format(value.normalize(), "f"))
    return normalized


def ungrounded_numbers(question: str, answer: str, tool_outputs: list[dict]) -> set[str]:
    """Numbers in an answer must come from the question or a tool output."""
    allowed = numbers_in(question)
    allowed.update(numbers_in(json.dumps(tool_outputs)))
    return numbers_in(answer) - allowed


def main() -> None:
    passed = 0
    for case in CASES:
        result = ask(case["question"])
        tools_called = {c["tool"] for c in result.tool_calls}
        ok, notes = True, []

        if case["expected_tools"]:
            if not tools_called & set(case["expected_tools"]):
                ok, notes = (
                    False,
                    [f"expected one of {case['expected_tools']}, got {sorted(tools_called)}"],
                )

        if case.get("must_not_forecast"):
            if not any(m in result.text.lower() for m in FORECAST_MARKERS):
                ok = False
                notes.append("expected a refusal/limitation statement for out-of-scope forecast")

        # Grounding: every number in the answer must appear in the question or
        # in a tool output. This also protects out-of-scope/refusal cases from
        # silently introducing unsupported current values.
        ungrounded = ungrounded_numbers(
            case["question"], result.text, [c["output"] for c in result.tool_calls]
        )
        if ungrounded:
            ok = False
            notes.append(f"ungrounded numbers in answer: {sorted(ungrounded)}")

        status = "PASS" if ok else "FAIL"
        passed += ok
        print(
            f"[{status}] {case['id']}: tools={sorted(tools_called)}"
            + (f" — {'; '.join(notes)}" if notes else "")
        )

    print(f"\n{passed}/{len(CASES)} cases passed")
    sys.exit(0 if passed == len(CASES) else 1)


if __name__ == "__main__":
    main()
