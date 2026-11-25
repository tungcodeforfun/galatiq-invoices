"""Payment agent: the only holder of mock_payment. Runs after the gate, retries declines, never pays twice."""

from __future__ import annotations

import hashlib
from typing import Any

from invoice_agents.db import Store
from invoice_agents.policy import Policy
from invoice_agents.schema import Invoice, Payment
from invoice_agents.tools import number_key, text_key


def mock_payment(vendor: str, amount: float) -> dict[str, Any]:
    """The mock banking API from the case brief."""
    print(f"Paid {amount} to {vendor}")
    return {"status": "success"}


def idempotency_key(invoice: Invoice, content: str) -> str:
    """One key per vendor, invoice number and content: the same bill can only ever be paid once."""
    raw = f"{text_key(invoice.vendor)}|{number_key(invoice.invoice_number)}|{content}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def pay(store: Store, invoice: Invoice, key: str, policy: Policy) -> Payment:
    """Pay once. A key already paid is not paid again; a key with an unknown result is not retried blindly."""
    vendor, amount, number = invoice.vendor or "", float(invoice.total or 0), invoice.invoice_number or ""
    existing = store.payment(key)
    if existing and existing["status"] == "success":
        return Payment(status="already_paid", idempotency_key=key, amount=amount, attempts=existing["attempts"],
                       detail="this invoice was paid before; no money moved")
    if existing and existing["status"] == "pending":
        return Payment(status="blocked", idempotency_key=key, amount=amount, attempts=existing["attempts"],
                       detail="an earlier attempt has no recorded result; reconcile with the bank first")
    attempts = existing["attempts"] if existing else 0
    result: dict[str, Any] = {}
    for _ in range(policy.payment_attempts):
        attempts += 1
        # Written before the call: if the process dies mid-call, the next run sees "pending" and stops.
        store.save_payment(key, number, vendor, amount, "pending", attempts)
        try:
            result = mock_payment(vendor, amount)
        except Exception as exc:
            # A timeout or dropped connection may still have moved money; only a reconciled answer may retry.
            return Payment(status="blocked", idempotency_key=key, amount=amount, attempts=attempts,
                           detail=f"{type(exc).__name__}: {exc}; result unknown, reconcile with the bank first")
        if result.get("status") == "success":
            store.save_payment(key, number, vendor, amount, "success", attempts)
            return Payment(status="success", idempotency_key=key, amount=amount, attempts=attempts)
        store.save_payment(key, number, vendor, amount, "failed", attempts)
    return Payment(status="failed", idempotency_key=key, amount=amount, attempts=attempts,
                   detail=f"bank declined {attempts} times: {result}")
