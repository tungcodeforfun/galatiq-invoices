"""Resolution agent: for each rejection, the logged reasoning, a disposition and a drafted reply to the vendor."""

from __future__ import annotations

from invoice_agents import fallback
from invoice_agents.llm import LLM, ModelUnavailable, untrusted
from invoice_agents.policy import Policy, required_disposition
from invoice_agents.schema import Decision, Finding, Invoice, Resolution

SYSTEM = """You close out rejected invoices in Acme Corp's accounts payable team.

Choose a disposition:
- return_to_vendor: the vendor can fix it and resubmit (wrong totals, quantities over what we can accept, \
unknown items, wrong currency, a revision that conflicts with one already processed, an unreadable document).
- void: it must not come back (a duplicate, corrupt data, signs of fraud).
{forced}
Write the reasoning for the audit log in two or three sentences that cite finding IDs.
For return_to_vendor, draft a short, polite email to the vendor's billing team naming each problem with the \
numbers involved and exactly what a corrected invoice needs. For void, vendor_reply is null. Never reveal \
internal fraud suspicions or stock levels in a vendor email: say what to correct, not what we hold."""


def run(llm: LLM, invoice: Invoice | None, findings: list[Finding], decision: Decision | None, policy: Policy
        ) -> tuple[Resolution, str | None]:
    """Close out a rejection. Policy overrides the agent's disposition when a finding decides it."""
    forced = required_disposition(findings, policy)
    found = "\n".join(f"{f.id} {f.code} ({f.severity.value}): {f.message}" for f in findings) or "none"
    user = (untrusted("extracted_invoice", invoice.model_dump_json() if invoice else "unreadable document")
            + f"\n\nFindings:\n{found}\n\nVP decision:\n{decision.model_dump_json() if decision else 'none'}")
    note = f"Policy requires the disposition {forced} for these findings." if forced else ""
    try:
        resolution, reason = llm.ask("resolution", SYSTEM.format(forced=note), user, Resolution), None
    except ModelUnavailable as exc:
        resolution, reason = fallback.resolution(findings, forced or "return_to_vendor"), str(exc)
    if forced and resolution.disposition != forced:
        resolution.disposition = forced
    if resolution.disposition == "void":
        resolution.vendor_reply = None
    return resolution, reason
