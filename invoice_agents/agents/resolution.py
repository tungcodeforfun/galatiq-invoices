"""Resolution agent: for each rejection, the logged reasoning, a disposition and a drafted reply to the vendor."""

from __future__ import annotations

from invoice_agents import fallback
from invoice_agents.llm import LLM, ModelUnavailable, findings_block, untrusted
from invoice_agents.schema import AgentDisposition, Decision, Finding, Invoice, Resolution, Severity

SYSTEM = """You close out rejected invoices in Acme Corp's accounts payable team.

Choose a disposition:
- return_to_vendor: the vendor can fix it and resubmit (wrong totals, quantities over what we can accept, \
unknown items, wrong currency, a revision that conflicts with one already processed, an unreadable document).
- void: it must not come back (a duplicate, corrupt data, signs of fraud).
{forced}
Write the reasoning for the audit log in two or three sentences that cite finding IDs.
For return_to_vendor, draft a short, polite email to the vendor's billing team naming each problem with the \
numbers involved and exactly what a corrected invoice needs. For void, vendor_reply is null. Never reveal \
internal fraud suspicions or stock levels in a vendor email: say what to correct, not what we hold. When a finding \
asks "did you mean" a catalog item, ask the vendor that question; never assume the answer."""


def run(llm: LLM, invoice: Invoice | None, findings: list[Finding], decision: Decision | None,
        forced: AgentDisposition | None) -> tuple[Resolution, str | None]:
    """Close out a rejection. Policy's disposition, when a finding decides it, overrides the agent's choice."""
    user = (untrusted("extracted_invoice", invoice.model_dump_json() if invoice else "unreadable document")
            + "\n\n" + findings_block(findings)
            + f"\n\nVP decision:\n{decision.model_dump_json() if decision else 'none'}")
    note = f"Policy requires the disposition {forced} for these findings." if forced else ""
    try:
        resolution, reason = llm.ask("resolution", SYSTEM.format(forced=note), user, Resolution), None
    except ModelUnavailable as exc:
        resolution, reason = fallback.resolution(findings, forced or "return_to_vendor"), str(exc)
    if forced and resolution.disposition != forced:
        rejected = ", ".join(f"{f.id} {f.code}" for f in findings if f.severity == Severity.REJECT)
        resolution.reasoning = (f"Policy requires {forced.replace('_', ' ')} for {rejected}; the resolution agent "
                                f"proposed {resolution.disposition.replace('_', ' ')}, so its reasoning is not used.")
        resolution.disposition = forced
    if resolution.disposition == "void":
        resolution.vendor_reply = None
    return resolution, reason
