"""LLM agent: Anthropic tool-use loop grounded in deterministic analytics.

Design principles
-----------------
1. The LLM never computes domain numbers itself — every quantitative claim must
   come from a tool result (grounding enforced by the system prompt and checked
   in evals).
2. Tools are deterministic and unit-tested; the LLM's job is orchestration,
   interpretation, and communication.
3. The loop is transparent: every tool call and result is surfaced to the caller.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from .schemas import TOOLS, run_tool

DEFAULT_MODEL = os.environ.get("COPILOT_MODEL", "claude-sonnet-5")
MAX_TURNS = 10

SYSTEM_PROMPT = """\
You are a supply-chain risk copilot for a forest products supply chain in
southern Sweden (Götaland/Småland region). You have tools backed by:
- REAL SMHI weather observations (wind gusts, 3 stations, recent months)
- REAL Swedish Forest Agency quarterly roundwood prices (2019Q1 onward)
- A SYNTHETIC illustrative 8-node supply network for what-if projections

Rules:
1. Every number you state must come from a tool result in this conversation.
   Never estimate, extrapolate, or recall domain numbers from training data.
2. When asked a quantitative what-if question, call stockout_whatif — do not
   compute projections yourself.
3. Always distinguish real data (weather, prices) from the synthetic network,
   and say so when the distinction matters to the user's decision.
4. If a tool returns an error or the data cannot answer the question, say so
   plainly and suggest what data would be needed.
5. Be concise and decision-oriented: lead with the answer, then the evidence.
"""


@dataclass
class AgentResult:
    text: str
    tool_calls: list[dict] = field(default_factory=list)
    turns: int = 0
    messages: list[dict] = field(default_factory=list)


def _client():
    try:
        import anthropic
    except ImportError as e:
        raise SystemExit(
            "The 'anthropic' package is required for agent mode: pip install anthropic"
        ) from e
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit(
            "ANTHROPIC_API_KEY is not set. Run `export ANTHROPIC_API_KEY=...` "
            "before starting agent mode — or try `python -m copilot.cli demo`, "
            "which needs no key."
        )
    return anthropic.Anthropic()


def ask(
    question: str, history: list[dict] | None = None, model: str = DEFAULT_MODEL
) -> AgentResult:
    """Run the tool-use loop for one user question. Returns final text + trace."""
    client = _client()
    messages = list(history or []) + [{"role": "user", "content": question}]
    result = AgentResult(text="")

    for _ in range(MAX_TURNS):
        result.turns += 1
        response = client.messages.create(
            model=model,
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            result.text = "".join(b.text for b in response.content if b.type == "text")
            result.messages = messages
            return result

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            output = run_tool(block.name, block.input)
            result.tool_calls.append({"tool": block.name, "input": block.input, "output": output})
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(output, ensure_ascii=False),
                }
            )
        messages.append({"role": "user", "content": tool_results})

    result.text = "(Stopped: exceeded maximum tool-use turns.)"
    result.messages = messages
    return result
