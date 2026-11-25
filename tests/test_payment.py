"""Unit tests for the payment agent: idempotency, retry, and no double payment after a failure."""

from __future__ import annotations

import pytest
from conftest import make_invoice

from invoice_agents.agents import payment


class Bank:
    """Stands in for the external banking API: fails a set number of times, then succeeds."""

    def __init__(self, failures: int = 0):
        self.failures = failures
        self.paid: list[tuple[str, float]] = []

    def __call__(self, vendor: str, amount: float) -> dict:
        if self.failures:
            self.failures -= 1
            raise ConnectionError("bank timeout")
        self.paid.append((vendor, amount))
        return {"status": "success"}


@pytest.fixture
def bank(monkeypatch):
    def install(failures: int = 0) -> Bank:
        fake = Bank(failures)
        monkeypatch.setattr(payment, "mock_payment", fake)
        return fake
    return install


def test_pays_once_and_refuses_the_same_key_again(store, policy, bank):
    fake = bank()
    invoice = make_invoice([("WidgetA", 2, 250)])
    assert payment.pay(store, invoice, "k1", policy).status == "success"
    assert payment.pay(store, invoice, "k1", policy).status == "already_paid"
    assert fake.paid == [("Widgets Inc.", 500.0)]


def test_transient_failure_is_retried_to_one_payment(store, policy, bank):
    fake = bank(failures=2)
    result = payment.pay(store, make_invoice([("WidgetA", 2, 250)]), "k2", policy)
    assert (result.status, result.attempts) == ("success", 3)
    assert len(fake.paid) == 1


def test_exhausted_retries_fail_and_a_later_run_pays_exactly_once(store, policy, bank):
    invoice = make_invoice([("WidgetA", 2, 250)])
    bank(failures=99)
    assert payment.pay(store, invoice, "k3", policy).status == "failed"
    assert store.payment("k3")["status"] == "failed"
    recovered = bank()
    assert payment.pay(store, invoice, "k3", policy).status == "success"
    assert payment.pay(store, invoice, "k3", policy).status == "already_paid"
    assert len(recovered.paid) == 1


def test_an_attempt_with_no_recorded_result_is_not_retried_blindly(store, policy, bank):
    fake = bank()
    store.save_payment("k4", "INV-9001", "Widgets Inc.", 500.0, "pending", 1)
    assert payment.pay(store, make_invoice([("WidgetA", 2, 250)]), "k4", policy).status == "blocked"
    assert fake.paid == []


def test_idempotency_key_ignores_layout_but_not_content():
    a = make_invoice([("WidgetA", 2, 250)], number="INV-1011")
    b = make_invoice([("WidgetA", 2, 250)], number="INV 1011")
    assert payment.idempotency_key(a, "h1") == payment.idempotency_key(b, "h1")
    assert payment.idempotency_key(a, "h1") != payment.idempotency_key(a, "h2")
