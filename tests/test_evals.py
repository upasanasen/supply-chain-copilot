"""Unit tests for the numeric-grounding evaluator (no model or API key)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evals"))

from run_evals import numbers_in, ungrounded_numbers


def test_number_normalization_handles_formatting_variants():
    assert numbers_in("1,252 SEK and -7.60%") == {"1252", "-7.6"}
    assert numbers_in('{"price": 1252.0, "change": -7.6}') == {"1252", "-7.6"}


def test_number_parser_ignores_digits_in_units_and_identifiers():
    assert numbers_in("1252 SEK/m3 from node H1") == {"1252"}


def test_grounding_allows_question_and_tool_numbers():
    ungrounded = ungrounded_numbers(
        "What happens for 6 weeks?",
        "Fill rate is 92.80% after 6 weeks.",
        [{"fill_rate_pct": 92.8}],
    )
    assert ungrounded == set()


def test_grounding_rejects_unsupported_numbers():
    assert ungrounded_numbers("What happens?", "Fill rate is 95%.", []) == {"95"}
