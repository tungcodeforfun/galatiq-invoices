"""Shared fixtures: a fresh database, the real policy, and a compact invoice builder."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from invoice_agents.db import Store
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
                 vendor: str = "Widgets Inc.", **fields) -> Invoice:
    """Invoice with the given (description, quantity, unit price) lines; total defaults to their sum."""
    items = [LineItem(description=d, quantity=q, unit_price=p, amount=None, note=None) for d, q, p in lines]
    base = dict(
        invoice_number=number, vendor=vendor, invoice_date="2026-01-15", due_date="2026-02-15",
        due_date_as_written="2026-02-15", currency="USD", line_items=items, subtotal=None, tax=None, shipping=None,
        total=sum(q * p for _, q, p in lines) if total is None else total, payment_terms="Net 30", notes=None,
        revision=None, corrections=[],
    )
    return Invoice(**{**base, **fields})
