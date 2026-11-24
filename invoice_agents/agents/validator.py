"""Validator agent: plans and runs the checks through tools; code supplies every number and every finding."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from invoice_agents.llm import LLM, ModelUnavailable, untrusted
from invoice_agents.schema import Invoice
from invoice_agents.tools import TOOL_SPECS, ToolBox

SYSTEM = """You are the validation analyst in Acme Corp's accounts payable team. You check one extracted invoice \
against the inventory catalog, the ledger of processed invoices and the vendor master, using the tools.

The tools do all arithmetic and lookups and record every problem they find. Never compute or estimate a number \
yourself, and never skip a check because the invoice looks clean.

Required checks:
1. resolve_item for every line.
2. check_stock once for every catalog item that appears, so quantities are summed across repeated lines.
3. check_price for every line that matched a catalog item.
4. check_totals, check_duplicate, and get_vendor with the vendor name as written.

Call independent tools together in one turn. When every check has run, report what you checked and anything a \
tool result suggests that the tools themselves would not flag."""


class ValidatorNotes(BaseModel):
    """What the validator checked and what it wants the approver to notice."""

    checks_run: list[str] = Field(description="Each tool call you made, e.g. 'check_stock(GadgetX)'")
    concerns: list[str] = Field(description="Points for the approver beyond what the tools flagged; may be empty")
    summary: str = Field(description="One or two sentences")


def run(llm: LLM, invoice: Invoice, tools: ToolBox, missing: list[tuple[str, dict[str, Any]]]
        ) -> tuple[ValidatorNotes | None, str | None]:
    """Let the agent run its checks. Returns (notes, degraded_reason)."""
    lines = "\n".join(f"{n}. {li.description}" for n, li in enumerate(invoice.line_items, 1))
    user = untrusted("extracted_invoice", invoice.model_dump_json(exclude={"corrections"})) + f"\n\nLines:\n{lines}"
    if missing:
        user += "\n\nA coverage check found these required checks have not run yet. Run them now:\n" + "\n".join(
            f"- {tool}({', '.join(f'{k}={v!r}' for k, v in args.items())})" for tool, args in missing
        )
    try:
        return llm.ask("validator", SYSTEM, user, ValidatorNotes, tools, list(TOOL_SPECS)), None
    except ModelUnavailable as exc:
        return None, str(exc)
