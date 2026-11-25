"""VP approver agent: drafts approve or reject with reasons that cite finding IDs, and revises after critique."""

from __future__ import annotations

from invoice_agents import fallback
from invoice_agents.llm import LLM, ModelUnavailable, findings_block, untrusted
from invoice_agents.policy import Policy
from invoice_agents.schema import Critique, Decision, Finding, Invoice, RiskMemo
from invoice_agents.tools import ToolBox

SYSTEM = """You are the VP of Finance at Acme Corp. You decide whether one vendor invoice gets paid.

Policy:
- A finding with severity "reject" means the invoice must not be paid. The payment gate blocks it whatever you \
decide, so approving it only shows you missed it.
- Warnings and info findings do not block payment on their own. Weigh them: approve when the invoice is still \
sound, and say why.
- Invoices over {threshold} need extra scrutiny: address every finding and the risk memo explicitly in your \
reasons.
- Reject a high-risk memo. A medium memo is yours to weigh: it does not on its own outweigh a vendor on file whose \
checks all pass, so name it in your reasons and decide on the evidence.
- You may reject for a reason no check caught when the document itself shows the problem. Doubts you cannot \
check here are not enough.
- Cite finding IDs in every reason they support. List every finding you considered in addressed_findings.

Be brief and concrete: a finance manager reads your summary."""


def brief(invoice: Invoice, findings: list[Finding], risk: RiskMemo | None) -> str:
    """The case file every reviewer sees: invoice, findings and risk memo."""
    memo = risk.model_dump_json() if risk else "not available"
    return (untrusted("extracted_invoice", invoice.model_dump_json()) + "\n\n" + findings_block(findings)
            + f"\n\nRisk memo (its quotes come from the invoice):\n{memo}")


def run(llm: LLM, invoice: Invoice, findings: list[Finding], risk: RiskMemo | None, tools: ToolBox,
        policy: Policy, previous: Decision | None, critique: Critique | None) -> tuple[Decision, str | None]:
    """Draft or revise the decision. Returns (decision, degraded_reason)."""
    user = brief(invoice, findings, risk)
    if previous and critique:
        user += (f"\n\nYour previous draft:\n{previous.model_dump_json()}\n\nA reviewer objected:\n"
                 + "\n".join(f"- {o}" for o in critique.objections)
                 + "\n\nRevise your decision. Change it only if the objections are right.")
    system = SYSTEM.format(threshold=f"${policy.approval_threshold:,.0f}")
    try:
        decision, reason = llm.ask("approver", system, user, Decision, tools, ["get_vendor"]), None
    except ModelUnavailable as exc:
        decision, reason = fallback.review(findings, risk), str(exc)
    known = {f.id for f in findings}
    decision.addressed_findings = [i for i in decision.addressed_findings if i in known]
    for r in decision.reasons:
        r.finding_ids = [i for i in r.finding_ids if i in known]
    return decision, reason


def needs_critique(invoice: Invoice, findings: list[Finding], policy: Policy, draft: Decision) -> bool:
    """The critic reviews any draft over the threshold, with a finding on file, or rejecting without one."""
    return bool(findings) or (invoice.total or 0) > policy.approval_threshold or draft.action == "reject"
