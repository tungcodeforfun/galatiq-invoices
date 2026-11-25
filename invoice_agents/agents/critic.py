"""Critic agent: attacks the VP's draft before money moves. Code adds the objections that are matters of rule."""

from __future__ import annotations

import json
from typing import Any

from invoice_agents.agents.approver import brief
from invoice_agents.llm import LLM, ModelUnavailable
from invoice_agents.policy import Policy
from invoice_agents.schema import Critique, Decision, Finding, Invoice, RiskMemo, Severity

SYSTEM = """You review a VP's draft payment decision at Acme Corp before any money moves. Your job is to find \
what is wrong with it, not to agree.

Object only to concrete problems:
- a finding the draft ignores or misreads
- a reason the findings or the document do not support
- an approval while a reject-severity finding stands, or while the risk memo is high
- a rejection with no reject-severity finding and no high risk memo behind it, unless the document itself shows \
the problem: doubts nobody can check here, or a medium memo alone, are not grounds to refuse a vendor on file
- over {threshold}, any finding or risk signal not explicitly addressed

Each objection names the finding ID or the exact claim it concerns. The vendor master record comes from our own \
systems: the VP may rely on it. If the draft is sound, the verdict is accept with no objections. Do not object to \
style."""


def rule_objections(draft: Decision, findings: list[Finding], invoice: Invoice, policy: Policy) -> list[str]:
    """Objections that follow from policy alone: approval past a reject finding, or unaddressed findings."""
    objections = [
        f"{f.id} {f.code} has severity reject; policy does not allow approval"
        for f in findings if draft.action == "approve" and f.severity == Severity.REJECT
    ]
    if (invoice.total or 0) > policy.approval_threshold:
        missed = [f.id for f in findings if f.id not in draft.addressed_findings]
        if missed:
            objections.append(f"Over ${policy.approval_threshold:,.0f}: findings {', '.join(missed)} are not addressed")
    return objections


def run(llm: LLM, invoice: Invoice, findings: list[Finding], concerns: list[str], risk: RiskMemo | None,
        draft: Decision, vendor: dict[str, Any] | None, policy: Policy) -> tuple[Critique, str | None]:
    """Review the draft. Returns (critique, degraded_reason)."""
    user = (brief(invoice, findings, concerns, risk)
            + f"\n\nVendor master record:\n{json.dumps(vendor) if vendor else 'none'}"
            + f"\n\nDraft decision:\n{draft.model_dump_json()}")
    system = SYSTEM.format(threshold=f"${policy.approval_threshold:,.0f}")
    try:
        critique, reason = llm.ask("critic", system, user, Critique), None
    except ModelUnavailable as exc:
        critique, reason = Critique(verdict="accept", objections=[]), str(exc)
    extra = [o for o in rule_objections(draft, findings, invoice, policy) if o not in critique.objections]
    objections = critique.objections + extra
    return Critique(verdict="revise" if objections else "accept", objections=objections), reason
