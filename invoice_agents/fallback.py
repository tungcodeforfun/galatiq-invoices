"""Degraded mode: rule-based stand-ins for each agent when there is no API key and no recording for the request."""

from __future__ import annotations

import re
from typing import Literal

from invoice_agents.rules import INSTRUCTION_LIKE, ocr_digits
from invoice_agents.schema import (
    AgentDisposition,
    Decision,
    Finding,
    Invoice,
    LineItem,
    Reason,
    Resolution,
    RiskMemo,
    Severity,
    Signal,
)
from invoice_agents.structured import free_text, read_structured, to_date, to_number

MONEY = r"\$?\s*(-?[\d,]+(?:\.\d+)?)"
VALUE = r"[ \t]*[:=][ \t]*(\S.*?)[ \t]*$"
FIELDS = {
    "invoice_number": r"(?:invoice\s*(?:number|no\.?|#)|inv\s*(?:no\.?|#)|invoice)\s*[:#]?\s*([A-Z]{0,4}[- ]?\d[\w-]*)",
    "vendor": r"^\s*(?:vendor(?:\s*name)?|vndr|supplier)" + VALUE,
    "sender": r"^\s*from" + VALUE,
    "invoice_date": r"^\s*(?:invoice\s*date|date|dt)" + VALUE,
    "due_date": r"^\s*(?:due\s*date|due\s*dt|due)" + VALUE,
    "subtotal": r"sub\s*-?total\s*[:=]?\s*" + MONEY,
    "tax": r"(?:sales\s*)?tax(?:_amount)?(?:\s*\([^)]*\))?\s*[:=]\s*" + MONEY,
    "shipping": r"(?:shipping|freight)\s*[:=]\s*" + MONEY,
    "total": r"^\s*(?:grand\s*total|total\s*amount|total|amt|amount\s*due)\s*[:=]?\s*" + MONEY,
    "currency": r"^\s*currency\s*[:=]\s*([A-Z]{3})",
    "payment_terms": r"^\s*(?:payment\s*terms|terms|pymnt\s*terms)" + VALUE,
    "notes": r"^\s*notes?" + VALUE,
}
LINE = re.compile(
    r"^\s*[-*]?\s*([A-Za-z][A-Za-z0-9 ()/.-]*?)\s+(?:qty:?\s*|x)?(-?\d+)\s+(?:@\s*|unit price:\s*)?"
    r"\$?([\d,]+(?:\.\d+)?)(?:\s*ea(?:ch)?)?(?:\s+\$?([\d,]+\.\d{2}))?\s*$",
    re.IGNORECASE,
)
LAYOUT_WORDS = {"invoice", "items", "item", "line", "description", "desc", "product", "qty", "quantity", "units",
                "unit", "price", "rate", "cost", "each", "amount", "total"}


def _item(line: str) -> LineItem | None:
    m = LINE.match(line)
    if not m or re.match(r"\s*(sub)?total|tax|date|due", m.group(1), re.IGNORECASE):
        return None
    return LineItem(description=m.group(1).strip(), quantity=to_number(m.group(2)), unit_price=to_number(m.group(3)),
                    amount=to_number(m.group(4)), note=None)


def extract(source: str) -> Invoice | None:
    """Read JSON, XML and CSV by field name, labelled text by pattern. None when no line items or total is found."""
    invoice = read_structured(source)
    if invoice is not None:
        return invoice
    text = ocr_digits(source)
    found: dict[str, str | None] = {}
    for name, pattern in FIELDS.items():
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        found[name] = match.group(1).strip() if match else None
    items = [item for line in text.splitlines() if (item := _item(line))]
    total = to_number(found["total"])
    if not items or total is None:
        return None
    return Invoice(
        invoice_number=found["invoice_number"], vendor=found["vendor"] or found["sender"],
        invoice_date=to_date(found["invoice_date"]),
        due_date=to_date(found["due_date"]), due_date_as_written=found["due_date"],
        currency=found["currency"] or ("USD" if "$" in source else None), line_items=items,
        subtotal=to_number(found["subtotal"]), tax=to_number(found["tax"]), shipping=to_number(found["shipping"]),
        total=total, payment_terms=found["payment_terms"], notes=found["notes"], revision=None, corrections=[],
    )


def _layout(line: str) -> bool:
    """Blank, a rule of dashes, a heading such as INVOICE, or a row of column names."""
    words = set(re.findall(r"[a-z]+", line.lower()))
    return not re.search(r"[A-Za-z0-9]", line) or (not re.search(r"\d", line) and words <= LAYOUT_WORDS)


def _read_line(line: str) -> bool:
    """Layout, a line item, or one labelled field (not notes) that fills the whole line."""
    if _layout(line) or _item(line):
        return True
    for name, pattern in FIELDS.items():
        m = re.match(rf"\s*(?:{pattern})", line, re.IGNORECASE | re.MULTILINE)
        if m and name != "notes" and not line[m.end():].strip():
            return True
    return False


def unread_text(source: str) -> list[str]:
    """Free text no rule reads: notes, prose fields of JSON, XML or CSV, and any other line of a text document."""
    found = free_text(source)
    if found is not None:
        return found
    return [line.strip() for line in ocr_digits(source).splitlines() if not _read_line(line)]


SIGNAL_WORDS: list[tuple[Literal["payment_redirect", "pressure_language"], str]] = [
    ("payment_redirect", r"wire transfer|bank details|account (?:number|details)|routing|iban|swift|remit to"),
    ("pressure_language", r"urgent|immediately|penalt|final notice|act now"),
]


def risk(source: str) -> RiskMemo:
    """Keyword screen for pressure, payment redirection and instruction injection, quoting the matching line."""
    signals = []
    for line in source.splitlines():
        if INSTRUCTION_LIKE.search(line):
            signals.append(Signal(kind="instruction_injection", quote=line.strip(), why="addresses the reviewer"))
        for kind, pattern in SIGNAL_WORDS:
            if re.search(pattern, line, re.IGNORECASE):
                signals.append(Signal(kind=kind, quote=line.strip(), why=f"matched the {kind} keyword list"))
    kinds = [s.kind for s in signals]
    high = "payment_redirect" in kinds or "instruction_injection" in kinds or kinds.count("pressure_language") > 1
    level: Literal["low", "medium", "high"] = "high" if high else "medium" if signals else "low"
    return RiskMemo(level=level, signals=signals, summary=f"Keyword screen found {len(signals)} signal(s).")


def review(findings: list[Finding], memo: RiskMemo | None) -> Decision:
    """Reject on any reject-severity finding or a high risk memo; otherwise approve."""
    blocking = [f for f in findings if f.severity == Severity.REJECT]
    reasons = [Reason(text=f.message, finding_ids=[f.id]) for f in blocking]
    if memo and memo.level == "high":
        reasons.append(Reason(text=f"High risk: {memo.summary}", finding_ids=[]))
    action: Literal["approve", "reject"] = "reject" if reasons else "approve"
    if not reasons:
        reasons = [Reason(text="All checks passed", finding_ids=[f.id for f in findings])]
    return Decision(action=action, reasons=reasons, addressed_findings=[f.id for f in findings],
                    summary=f"Rule-based review: {action}.")


def resolution(findings: list[Finding], disposition: AgentDisposition) -> Resolution:
    """List the problems; draft a plain correction request when the vendor can fix them."""
    problems = [f"{f.id} {f.code}: {f.message}" for f in findings if f.severity == Severity.REJECT]
    reasoning = "Rejected: " + ("; ".join(problems) or "the approver rejected it")
    reply = None
    if disposition == "return_to_vendor":
        reply = ("Hello,\n\nWe could not process this invoice:\n"
                 + "\n".join(f"- {f.message}" for f in findings if f.severity == Severity.REJECT)
                 + "\n\nPlease send a corrected invoice.\n\nAccounts Payable, Acme Corp")
    return Resolution(disposition=disposition, reasoning=reasoning, vendor_reply=reply)


STEP_NAMES = {"intake": "Intake", "validator": "Validator", "risk": "Risk", "approver": "VP", "critic": "Critic",
              "resolution": "Resolution"}


def notice(agents: list[str], live: bool, reset: str = "`python main.py reset`") -> str:
    """One plain sentence or two for whoever reads the result: which steps Grok didn't answer, and what to do."""
    if not agents:
        return ""
    steps = ", ".join(STEP_NAMES.get(a, a) for a in agents)
    if live:
        return f"Grok did not answer for {steps}, so built-in rules handled those steps. The run log has the error."
    if "intake" in agents:
        return ("Grok has no recorded answer for this file and no API key is set, so built-in rules read it. "
                "Rules pay only clean invoices under the approval limit. Set XAI_API_KEY to have Grok read it.")
    return (f"No recording exists for this ledger state, so {steps} used built-in rules. "
            f"{reset} replays Grok's recorded answers, or set XAI_API_KEY.")
