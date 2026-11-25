"""Unit tests for the policy gate and dispositions: an agent can be stricter than policy, never looser."""

from __future__ import annotations

from invoice_agents.policy import NO_MODEL, gate, required_disposition
from invoice_agents.schema import Critique, Decision, Reason

ACCEPTED = [Critique(verdict="accept", objections=[])]
OPEN = [Critique(verdict="revise", objections=["F1 not addressed"])]


def decision(action: str) -> Decision:
    return Decision(action=action, reasons=[Reason(text="x", finding_ids=[])], addressed_findings=[], summary="x")


def numbered(*findings):
    return [f.model_copy(update={"id": f"F{n}"}) for n, f in enumerate(findings, 1)]


def test_clean_approval_passes(policy):
    assert gate(decision("approve"), [], 5000.0, [], [], False, policy).approved


def test_approval_with_a_reject_finding_is_overridden(policy):
    findings = numbered(policy.finding("STOCK_EXCEEDED", "GadgetX: 20 requested, 5 in stock", "test"))
    result = gate(decision("approve"), findings, 15000.0, ACCEPTED, [], False, policy)
    assert not result.approved
    assert result.blocked_by == ["F1 STOCK_EXCEEDED"]


def test_warnings_alone_do_not_block(policy):
    findings = numbered(policy.finding("PRICE_VARIANCE", "rush line", "test"))
    assert gate(decision("approve"), findings, 7185.0, ACCEPTED, [], False, policy).approved


def test_over_threshold_needs_critic_review(policy):
    assert not gate(decision("approve"), [], 12000.0, [], [], False, policy).approved
    assert gate(decision("approve"), [], 12000.0, ACCEPTED, [], False, policy).approved


def test_open_critic_objections_block_payment_over_the_threshold(policy):
    assert not gate(decision("approve"), [], 12000.0, ACCEPTED + OPEN, [], False, policy).approved
    assert gate(decision("approve"), [], 7185.0, ACCEPTED + OPEN, [], False, policy).approved


def test_a_required_check_that_never_ran_blocks_payment(policy):
    result = gate(decision("approve"), [], 500.0, [], ["check_duplicate({})"], False, policy)
    assert not result.approved


def test_rejection_is_never_turned_into_payment(policy):
    assert not gate(decision("reject"), [], 100.0, ACCEPTED, [], False, policy).approved


def test_nothing_to_pay_is_blocked(policy):
    assert not gate(decision("approve"), [], -250.0, ACCEPTED, [], False, policy).approved


def test_an_approved_clean_run_with_any_step_made_without_a_model_is_never_paid(policy):
    held = gate(decision("approve"), [], 500.0, ACCEPTED, [], True, policy)
    assert not held.approved and held.blocked_by == [NO_MODEL]
    assert gate(decision("approve"), [], 500.0, ACCEPTED, [], False, policy).approved


def test_void_beats_return_to_vendor(policy):
    findings = [policy.finding("TOTAL_MISMATCH", "x", "t"), policy.finding("DUPLICATE", "y", "t")]
    assert required_disposition(findings, policy) == "void"
    assert required_disposition(findings[:1], policy) == "return_to_vendor"
    assert required_disposition([policy.finding("PRICE_VARIANCE", "z", "t")], policy) is None
