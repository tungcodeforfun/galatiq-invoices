"""Shared fixtures: a fresh database, the real policy, a compact invoice builder and a scripted model."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel

from invoice_agents.db import Store
from invoice_agents.llm import CASSETTES, LLM, ModelUnavailable, request_key
from invoice_agents.policy import Policy, load_policy
from invoice_agents.schema import Invoice, LineItem

os.environ.setdefault("LLM_MODE", "replay")


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(tmp_path / "test.db")


@pytest.fixture
def policy() -> Policy:
    return load_policy()


def make_invoice(lines: list[tuple[str, float, float]], total: float | None = None, number: str = "INV-9001",
                 vendor: str | None = "Widgets Inc.", **fields) -> Invoice:
    """Invoice with the given (description, quantity, unit price) lines; total defaults to their sum."""
    items = [LineItem(description=d, quantity=q, unit_price=p, amount=None, note=None) for d, q, p in lines]
    base = dict(
        invoice_number=number, vendor=vendor, invoice_date="2026-01-15", due_date="2026-02-15",
        due_date_as_written="2026-02-15", currency="USD", line_items=items, subtotal=None, tax=None, shipping=None,
        total=sum(q * p for _, q, p in lines) if total is None else total, payment_terms="Net 30", notes=None,
        revision=None, corrections=[],
    )
    return Invoice(**{**base, **fields})


class ScriptedLLM(LLM):
    """Gives the named agents a fixed answer and the committed recordings to the rest, recording every exchange."""

    def __init__(self, cassettes: Path, answers: dict[str, BaseModel]):
        super().__init__(mode="cached", cassettes=cassettes)
        self.answers = answers

    def _live(self, agent: str, messages: list[dict[str, Any]], tools: list[dict[str, Any]],
              response_format: dict[str, Any]) -> dict[str, Any]:
        if agent in self.answers:
            return {"choices": [{"message": {"content": self.answers[agent].model_dump_json()}}], "usage": {}}
        recorded = CASSETTES / f"{request_key(self.model, messages, tools, response_format)}.json"
        if not recorded.exists():
            raise ModelUnavailable("no recording for this request")
        return json.loads(recorded.read_text())["response"]
