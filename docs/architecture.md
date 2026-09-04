# Architecture

## Components

```
scripts/                 Data acquisition (run once; re-runnable)
  fetch_smhi_wind.py       SMHI metobs API → data/raw + data/processed/wind_daily.csv
  fetch_prices_pxweb.py    Skogsstyrelsen PxWeb → data/processed/prices_quarterly.csv
  manifest.py              SHA-256 + provenance for every raw file

src/copilot/
  tools/                 Deterministic analytics (stdlib only, unit-tested)
    weather_risk.py        storm_risk_summary, recent_gusts
    price_trends.py        price_summary, price_series
    inventory.py           network_summary, stockout_whatif
    report.py              risk_snapshot (combined)
  schemas.py             Tool JSON schemas for the LLM + dispatch table
  agent.py               Anthropic tool-use loop (ask → tools → grounded answer)
  cli.py                 demo / report / chat / ask commands

tests/                   14 pytest cases: tool correctness, validation,
                         monotonicity, mocked agent loop, loop termination
evals/                   Golden questions + numeric-grounding harness
```

## The agent loop

`agent.ask()` implements a standard tool-use loop with three deliberate constraints:

1. **Bounded**: at most `MAX_TURNS` model calls, with an explicit truncation message.
2. **Traceable**: every tool call (name, input, output) is returned to the caller
   in `AgentResult.tool_calls`, and the CLI prints them, so a user always sees
   *why* the agent answered what it answered.
3. **Grounded**: the system prompt forbids numbers that don't come from tool
   results; the eval harness checks this by extracting every numeric token from
   the answer and requiring it to appear in the serialized tool outputs.

## Why the LLM doesn't do the math

LLMs are unreliable at arithmetic and irresistibly confident about it. In a
supply-chain setting, a hallucinated "weeks to stockout" is worse than no
answer. So the division of labor is strict:

- **Python tools**: everything with a correct answer (thresholds, deltas,
  projections, concentration indices). Testable, reviewable, deterministic.
- **LLM**: everything without one (which tool answers this question, what does
  the result mean for the decision, how to say it clearly, when to caveat).

This mirrors how a good human analyst works: the spreadsheet computes, the
analyst interprets.

## Extending

- Add a tool: implement it under `tools/`, register schema + dispatch in
  `schemas.py`, add a unit test and (if user-facing) a golden question.
- Swap the network: replace `data/synthetic/network.csv` with a real network
  extract; `inventory.py` reads any CSV with the same columns.
- Live weather: schedule `fetch_smhi_wind.py`; the tools always read the latest
  processed CSVs, so the agent picks up fresh data with no code change.
