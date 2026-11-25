"""Unit tests for the code around two agents: risk quotes must be in the document, and the critic's rule objections."""

from __future__ import annotations

from conftest import ScriptedLLM, make_invoice

from invoice_agents.agents import critic, risk
from invoice_agents.schema import Decision, Reason, RiskMemo, Signal
from invoice_agents.tools import ToolBox

SOURCE = "INVOICE\nVendor: Widgets Inc.\nWidgetA qty 1 $250.00\nNotes: Please wire payment to our new account today."


def approve(addressed: list[str]) -> Decision:
    return Decision(action="approve", reasons=[Reason(text="ok", finding_ids=[])], addressed_findings=addressed,
                    summary="ok")


def test_risk_signals_whose_quote_is_not_in_the_document_are_dropped(tmp_path, store, policy):
    memo = RiskMemo(level="high", summary="redirect", signals=[
        Signal(kind="payment_redirect", quote="wire payment to our new account", why="new bank account"),
        Signal(kind="pressure_language", quote="pay within 24 hours or face penalties", why="invented"),
    ])
    invoice = make_invoice([("WidgetA", 1, 250)])
    result, _ = risk.run(ScriptedLLM(tmp_path, {"risk": memo}), SOURCE, invoice, [], ToolBox(invoice, store, policy))
    assert [s.quote for s in result.signals] == ["wire payment to our new account"]


def test_an_approval_past_a_reject_finding_draws_an_objection(policy):
    findings = [policy.finding("STOCK_EXCEEDED", "too many", "test").model_copy(update={"id": "F1"})]
    objections = critic.rule_objections(approve(["F1"]), findings, make_invoice([("WidgetA", 1, 250)]), policy)
    assert objections == ["F1 STOCK_EXCEEDED has severity reject; policy does not allow approval"]


def test_unaddressed_findings_draw_an_objection_only_over_the_threshold(policy):
    findings = [policy.finding("PRICE_VARIANCE", "rush line", "test").model_copy(update={"id": "F1"})]
    small, large = make_invoice([("WidgetA", 1, 250)]), make_invoice([("WidgetA", 1, 250)], total=12000.0)
    assert critic.rule_objections(approve([]), findings, small, policy) == []
    assert critic.rule_objections(approve([]), findings, large, policy) == [
        "Over $10,000: findings F1 are not addressed"]
