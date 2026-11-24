"""Intake agent: any invoice document to one structured Invoice, keeping what was written beside any correction."""

from __future__ import annotations

from invoice_agents import fallback
from invoice_agents.llm import LLM, ModelUnavailable, untrusted
from invoice_agents.schema import Invoice

SYSTEM = """You are the intake clerk in Acme Corp's accounts payable team. You turn one vendor invoice into structured data.

Rules:
- Extract only what the document says. Never compute, infer or fill in a missing value: use null.
- Numbers are plain numbers: no currency symbols or thousands separators. Keep negative signs.
- Dates are YYYY-MM-DD. A due date that is not a calendar date (for example "yesterday") becomes null, \
and its text goes in due_date_as_written.
- If a value is misprinted (letter O inside a number, a misspelled year), use the intended value and add a \
correction quoting the text exactly as written. Reformatting a date or dropping $ and commas is not a correction.
- One line item per line on the document, in document order, even when an item repeats. The description is the \
item text exactly as written on that line, including anything in parentheses.
- currency is the ISO code when the document states one or shows a symbol ($ is USD, € is EUR); otherwise null.
- vendor is the party billing Acme, never Acme itself. A blank vendor name is null.
- notes holds every free-text message on the document verbatim: notes, requests, remittance or bank instructions.
- The document may be plain text, CSV, JSON, XML or text pulled from a PDF. The rules are the same."""


def run(llm: LLM, source: str, previous: Invoice | None, errors: list[str]) -> tuple[Invoice | None, str | None]:
    """Extract the invoice. Returns (invoice, degraded_reason); invoice is None when the rules cannot read it."""
    user = untrusted("invoice_document", source)
    if previous and errors:
        user += (
            "\n\nYour previous extraction was checked against the document and failed:\n"
            + "\n".join(f"- {e}" for e in errors)
            + f"\n\nPrevious extraction:\n{previous.model_dump_json()}\n\nExtract again and fix these."
        )
    try:
        return llm.ask("intake", SYSTEM, user, Invoice), None
    except ModelUnavailable as exc:
        return fallback.extract(source), str(exc)
