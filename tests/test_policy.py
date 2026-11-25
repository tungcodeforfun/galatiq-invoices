"""Unit tests for the policy gate and dispositions: an agent can be stricter than policy, never looser."""

from __future__ import annotations

from invoice_agents.policy import gate, required_disposition
from invoice_agents.schema import Decision, Reason


def decision(action: str) -> Decision:
    return Decision(action=action, reasons=[Reason(text="x", finding_ids=[])], addressed_findings=[], summary="x")


def numbered(*findings):
    return [f.model_copy(update={"id": f"F{n}"}) for n, f in enumerate(findings, 1)]


def test_clean_approval_passes(policy):
    assert gate(decision("approve"), [], 5000.0, 0, False, policy).approved


def test_approval_with_a_reject_finding_is_overridden(policy):
    findings = numbered(policy.finding("STOCK_EXCEEDED", "GadgetX: 20 requested, 5 in stock", "test"))
    result = gate(decision("approve"), findings, 15000.0, 1, False, policy)
    assert not result.approved and result.overridden
    assert result.blocked_by == ["F1 STOCK_EXCEEDED"]


def test_warnings_alone_do_not_block(policy):
    findings = numbered(policy.finding("PRICE_VARIANCE", "rush line", "test"))
    assert gate(decision("approve"), findings, 7185.0, 1, False, policy).approved


def test_over_threshold_needs_critic_review(policy):
    assert not gate(decision("approve"), [], 12000.0, 0, False, policy).approved
    assert gate(decision("approve"), [], 12000.0, 1, False, policy).approved


def test_rejection_is_never_turned_into_payment(policy):
    assert not gate(decision("reject"), [], 100.0, 1, False, policy).approved


def test_nothing_to_pay_is_blocked(policy):
    assert not gate(decision("approve"), [], -250.0, 1, False, policy).approved


def test_degraded_mode_pays_only_spotless_invoices_under_threshold(policy):
    warn = numbered(policy.finding("DATE_ODDITY", "no due date", "test"))
    info = numbered(policy.finding("NEW_VENDOR", "unknown", "test"))
    assert not gate(decision("approve"), warn, 500.0, 1, True, policy).approved
    assert not gate(decision("approve"), [], 12000.0, 1, True, policy).approved
    assert gate(decision("approve"), info, 500.0, 0, True, policy).approved


def test_void_beats_return_to_vendor(policy):
    findings = [policy.finding("TOTAL_MISMATCH", "x", "t"), policy.finding("DUPLICATE", "y", "t")]
    assert required_disposition(findings, policy) == "void"
    assert required_disposition(findings[:1], policy) == "return_to_vendor"
    assert required_disposition([policy.finding("PRICE_VARIANCE", "z", "t")], policy) is None
