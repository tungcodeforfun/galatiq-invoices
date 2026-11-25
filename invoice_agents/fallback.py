"""Degraded mode: rule-based stand-ins for each agent when there is no API key and no recording for the request."""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Literal

from invoice_agents.rules import INSTRUCTION_LIKE, ocr_digits
from invoice_agents.schema import (
    Decision,
    Disposition,
    Finding,
    Invoice,
    LineItem,
    Reason,
    Resolution,
    RiskMemo,
    Severity,
    Signal,
)

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
DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%B %d, %Y", "%b %d %Y", "%d-%b-%Y", "%b %d, %Y")


def _flatten(text: str) -> str:
    """Turn JSON or XML into 'key: value' lines so one set of patterns reads every format."""
    try:
        data = json.loads(text)
    except ValueError:
        return re.sub(r"<(\w+)>([^<]*)</\1>", r"\1: \2", text)
    lines: list[str] = []

    def walk(node: Any, key: str = "") -> None:
        if isinstance(node, dict):
            if {"item", "quantity"} <= node.keys() or {"name", "quantity"} <= node.keys():
                name = node.get("item") or node.get("name")
                lines.append(f"{name}  {node['quantity']}  {node.get('unit_price', '')}")
                return
            for k, v in node.items():
                walk(v, "vendor" if k == "vendor" and isinstance(v, dict) else k)
        elif isinstance(node, list):
            for v in node:
                walk(v, key)
        elif key:
            lines.append(f"{'vendor' if key == 'name' else key}: {node}")

    walk(data)
    return "\n".join(lines).replace("invoice_number:", "invoice number:").replace("due_date:", "due date:")


def _number(raw: str | None) -> float | None:
    try:
        return float(raw.replace(",", "")) if raw else None
    except ValueError:
        return None


def _date(raw: str | None) -> str | None:
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime((raw or "").strip(), fmt).date().isoformat()
        except ValueError:
            continue
    return None


def extract(source: str) -> Invoice | None:
    """Pattern-based extraction. Returns None when the document has no line items or no total it can read."""
    text = ocr_digits(_flatten(source))
    found: dict[str, str | None] = {}
    for name, pattern in FIELDS.items():
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        found[name] = match.group(1).strip() if match else None
    items = []
    for line in text.splitlines():
        m = LINE.match(line)
        if m and not re.match(r"\s*(sub)?total|tax|date|due", m.group(1), re.IGNORECASE):
            items.append(LineItem(description=m.group(1).strip(), quantity=_number(m.group(2)),
                                  unit_price=_number(m.group(3)), amount=_number(m.group(4)), note=None))
    total = _number(found["total"])
    if not items or total is None:
        return None
    return Invoice(
        invoice_number=found["invoice_number"], vendor=found["vendor"] or found["sender"],
        invoice_date=_date(found["invoice_date"]),
        due_date=_date(found["due_date"]), due_date_as_written=found["due_date"],
        currency=found["currency"] or ("USD" if "$" in source else None), line_items=items,
        subtotal=_number(found["subtotal"]), tax=_number(found["tax"]), shipping=_number(found["shipping"]),
        total=total, payment_terms=found["payment_terms"], notes=found["notes"], revision=None, corrections=[],
    )


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


def resolution(findings: list[Finding], disposition: Disposition) -> Resolution:
    """List the problems; draft a plain correction request when the vendor can fix them."""
    problems = [f"{f.id} {f.code}: {f.message}" for f in findings if f.severity == Severity.REJECT]
    reasoning = "Rejected: " + ("; ".join(problems) or "the approver rejected it")
    reply = None
    if disposition == "return_to_vendor":
        reply = ("Hello,\n\nWe could not process this invoice:\n"
                 + "\n".join(f"- {f.message}" for f in findings if f.severity == Severity.REJECT)
                 + "\n\nPlease send a corrected invoice.\n\nAccounts Payable, Acme Corp")
    return Resolution(disposition=disposition, reasoning=reasoning, vendor_reply=reply)
