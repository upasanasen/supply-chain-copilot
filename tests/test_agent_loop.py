"""Agent-loop tests with a mocked Anthropic client (no API key, no network)."""

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from copilot import agent


class FakeBlock(SimpleNamespace):
    pass


def _text_response(text):
    return SimpleNamespace(
        stop_reason="end_turn",
        content=[FakeBlock(type="text", text=text)],
    )


def _tool_response(name, tool_input, tool_id="t1"):
    return SimpleNamespace(
        stop_reason="tool_use",
        content=[FakeBlock(type="tool_use", name=name, input=tool_input, id=tool_id)],
    )


class FakeClient:
    def __init__(self, responses):
        self._responses = list(responses)
        self.requests = []
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.requests.append(kwargs)
        return self._responses.pop(0)


def test_direct_answer_no_tools():
    fake = FakeClient([_text_response("Hello!")])
    with patch.object(agent, "_client", return_value=fake):
        result = agent.ask("hi")
    assert result.text == "Hello!"
    assert result.tool_calls == []
    assert result.turns == 1


def test_tool_use_round_trip_executes_real_tool():
    fake = FakeClient(
        [
            _tool_response("network_summary", {}),
            _text_response("The network has 8 nodes."),
        ]
    )
    with patch.object(agent, "_client", return_value=fake):
        result = agent.ask("describe the network")
    assert result.turns == 2
    assert result.tool_calls[0]["tool"] == "network_summary"
    assert len(result.tool_calls[0]["output"]["nodes"]) == 8
    # The tool result must be sent back to the model in the conversation.
    tool_result_msgs = [
        m
        for m in fake.requests[1]["messages"]
        if isinstance(m.get("content"), list)
        and m["content"]
        and isinstance(m["content"][0], dict)
        and m["content"][0].get("type") == "tool_result"
    ]
    assert tool_result_msgs, "no tool_result message sent back to the model"
    assert result.messages[-1]["role"] == "assistant"
    assert any(
        message["role"] == "user"
        and isinstance(message["content"], list)
        and message["content"]
        and message["content"][0].get("type") == "tool_result"
        for message in result.messages
    )


def test_loop_terminates_at_max_turns():
    fake = FakeClient([_tool_response("network_summary", {})] * agent.MAX_TURNS)
    with patch.object(agent, "_client", return_value=fake):
        result = agent.ask("loop forever")
    assert result.turns == agent.MAX_TURNS
    assert "maximum tool-use turns" in result.text


def test_complete_history_can_be_reused_for_follow_up():
    first_client = FakeClient(
        [_tool_response("network_summary", {}), _text_response("The network has 8 nodes.")]
    )
    with patch.object(agent, "_client", return_value=first_client):
        first = agent.ask("describe the network")

    second_client = FakeClient([_text_response("Here is the follow-up.")])
    with patch.object(agent, "_client", return_value=second_client):
        agent.ask("which are demand nodes?", history=first.messages)

    follow_up_messages = second_client.requests[0]["messages"]
    assert follow_up_messages[:-2] == first.messages
    assert follow_up_messages[-2] == {"role": "user", "content": "which are demand nodes?"}
    assert any(
        message["role"] == "user"
        and isinstance(message["content"], list)
        and message["content"][0].get("type") == "tool_result"
        for message in follow_up_messages
    )
