"""Unit tests for recordings: the request key, replay of a tool-calling exchange, and a miss in replay mode."""

from __future__ import annotations

import json

import pytest
from pydantic import BaseModel

from invoice_agents.llm import LLM, MODEL, ModelUnavailable, request_key, structured_output


class Answer(BaseModel):
    in_stock: int


class StockTools:
    def __init__(self):
        self.calls: list[dict] = []

    def specs(self, names):
        return [{"type": "function", "function": {"name": "check_stock", "parameters": {"type": "object"}}}]

    def call(self, name, args, by="agent"):
        self.calls.append(args)
        return {"item": args["item"], "stock": 15}


def save(cassettes, messages, tools, body):
    key = request_key(MODEL, messages, tools, structured_output(Answer))
    (cassettes / f"{key}.json").write_text(json.dumps({"request_sha256": key, "response": body}))


def reply(message):
    return {"choices": [{"message": message}], "usage": {}}


def test_request_key_ignores_dict_order_but_not_content():
    a = request_key("m", [{"role": "user", "content": "hi"}], [], {"x": 1, "y": 2})
    assert a == request_key("m", [{"content": "hi", "role": "user"}], [], {"y": 2, "x": 1})
    assert a != request_key("m", [{"role": "user", "content": "hi!"}], [], {"x": 1, "y": 2})


def test_replay_reruns_the_tools_and_returns_the_recorded_answer(tmp_path):
    tools = StockTools()
    first = [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}]
    call = {"id": "c1", "type": "function", "function": {"name": "check_stock", "arguments": '{"item": "WidgetA"}'}}
    save(tmp_path, first, tools.specs([]), reply({"content": "", "tool_calls": [call]}))
    second = first + [{"role": "assistant", "content": "", "tool_calls": [call]},
                      {"role": "tool", "tool_call_id": "c1", "content": json.dumps({"item": "WidgetA", "stock": 15})}]
    save(tmp_path, second, tools.specs([]), reply({"content": '{"in_stock": 15}'}))

    seen: list[str] = []
    llm = LLM(mode="replay", cassettes=tmp_path, on_call=lambda **e: seen.append(e["tier"]))
    assert llm.ask("validator", "s", "u", Answer, tools, ["check_stock"]) == Answer(in_stock=15)
    assert tools.calls == [{"item": "WidgetA"}]
    assert seen == ["replay", "replay"]


def test_replay_without_a_recording_raises_instead_of_calling_the_api(tmp_path):
    with pytest.raises(ModelUnavailable):
        LLM(mode="replay", cassettes=tmp_path).ask("intake", "s", "changed prompt", Answer)
