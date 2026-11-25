"""Degraded mode: rule-based stand-ins for each agent when there is no API key and no recording for the request."""

from __future__ import annotations

import csv
import io
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any, Literal

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
from invoice_agents.tools import text_key

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
DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%B %d, %Y", "%b %d %Y", "%d-%b-%Y", "%b %d, %Y", "%d %B %Y", "%d %b %Y")

FIELD_NAMES = {
    "invoice_number": {"invoicenumber", "invoiceno", "invoicenum", "invoiceid", "invoice", "number", "invno",
                       "documentnumber", "billnumber"},
    "vendor": {"vendor", "vendorname", "supplier", "suppliername", "seller", "sellername", "billfrom", "from",
               "payee", "issuer", "company", "companyname", "name"},
    "invoice_date": {"date", "invoicedate", "issuedate", "dateissued", "issued", "billdate"},
    "due_date": {"duedate", "due", "paymentdue", "datedue", "payby"},
    "currency": {"currency", "currencycode", "curr"},
    "subtotal": {"subtotal", "nettotal", "netamount"},
    "tax": {"tax", "taxamount", "vat", "vatamount", "salestax", "gst"},
    "shipping": {"shipping", "freight", "delivery", "shippingcost", "shippingamount"},
    "total": {"total", "totalamount", "amountdue", "grandtotal", "totaldue", "balancedue", "invoicetotal"},
    "payment_terms": {"paymentterms", "terms"},
    "notes": {"notes", "note", "memo", "comments", "comment", "remarks", "message"},
}
LINE_NAMES = {
    "description": {"description", "item", "name", "product", "itemname", "productname", "itemdescription", "desc",
                    "sku", "part"},
    "quantity": {"quantity", "qty", "units", "count"},
    "unit_price": {"unitprice", "price", "rate", "unitcost", "priceeach", "each", "cost"},
    "amount": {"amount", "linetotal", "total", "extended", "lineamount"},
    "note": {"note", "notes", "comment", "remark"},
}
OTHER_PARTIES = {"buyer", "billto", "customer", "shipto", "client", "soldto", "to"}


def _key(name: Any) -> str:
    return text_key(re.sub(r"\(.*?\)", "", str(name)))


def _field(names: dict[str, set[str]], key: str) -> str | None:
    return next((field for field, aliases in names.items() if key in aliases), None)


def _number(raw: Any) -> float | None:
    try:
        return float(re.sub(r"[^\d.\-]", "", str(raw))) if raw not in (None, "") else None
    except ValueError:
        return None


def _date(raw: Any) -> str | None:
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(str(raw or "").strip(), fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _line(record: dict[str, Any]) -> dict[str, Any] | None:
    """The line-item fields of a record that has both a description and a quantity, else None."""
    line: dict[str, Any] = {}
    for k, v in record.items():
        field = _field(LINE_NAMES, _key(k))
        if field and not isinstance(v, dict | list) and not (isinstance(v, str) and not v.strip()):
            line.setdefault(field, v)
    return line if {"description", "quantity"} <= line.keys() else None


def _collect(node: Any, fields: dict[str, Any], lines: list[dict[str, Any]]) -> None:
    """Walk a parsed document: records with a description and quantity are lines, scalars are invoice fields."""
    if isinstance(node, list):
        for child in node:
            _collect(child, fields, lines)
        return
    if not isinstance(node, dict):
        return
    line = _line(node)
    if line:
        lines.append(line)
        return
    for k, v in node.items():
        key, field = _key(k), _field(FIELD_NAMES, _key(k))
        if key in OTHER_PARTIES:
            continue
        if isinstance(v, dict) and field == "vendor":
            name = next((x for n, x in v.items() if _key(n) in FIELD_NAMES["vendor"] and isinstance(x, str)), None)
            fields.setdefault("vendor", name)
        elif isinstance(v, dict | list):
            _collect(v, fields, lines)
        elif field:
            fields.setdefault(field, v)


def _xml_tree(element: ET.Element) -> Any:
    children = list(element)
    if not children:
        return (element.text or "").strip()
    tree: dict[str, Any] = {}
    for child in children:
        value = _xml_tree(child)
        if child.tag in tree:
            existing = tree[child.tag]
            tree[child.tag] = (existing if isinstance(existing, list) else [existing]) + [value]
        else:
            tree[child.tag] = value
    return tree


def _pairs_tree(pairs: list[list[str]]) -> dict[str, Any]:
    """field,value rows; a description starts a line item and the item fields after it belong to that line."""
    tree: dict[str, Any] = {}
    lines: list[dict[str, str]] = []
    open_line: dict[str, str] | None = None
    for k, v in pairs:
        field = _field(LINE_NAMES, _key(k))
        if field == "description":
            open_line = {k: v}
            lines.append(open_line)
        elif field and open_line is not None and _key(k) not in FIELD_NAMES["total"]:
            open_line.setdefault(k, v)
        else:
            open_line = None
            tree.setdefault(k, v)
    return tree | {"lines": lines}


def _csv_tree(text: str) -> dict[str, Any] | None:
    """A CSV invoice as a tree: field,value pairs, or a header with one row per line item and summary rows."""
    rows = [r for r in csv.reader(io.StringIO(text)) if any(c.strip() for c in r)]
    if len(rows) < 2 or len({len(r) for r in rows}) != 1 or len(rows[0]) < 2:
        return None
    if len(rows[0]) == 2:
        return _pairs_tree(rows[1:] if _key(rows[0][0]) == "field" else rows)
    records = [dict(zip(rows[0], r, strict=True)) for r in rows[1:]]
    lines = [r for r in records if _line(r)]
    if not lines:
        return None
    summary = {}
    for r in records:
        cells = [c.strip() for c in r.values() if c.strip()]
        if r not in lines and len(cells) >= 2:
            summary[cells[0]] = cells[-1]
    first = {k: v for k, v in lines[0].items() if not _field(LINE_NAMES, _key(k))}
    return first | summary | {"lines": lines}


def _structured(source: str) -> Any:
    """Parse JSON, XML or CSV into dicts and lists; None when the document is none of them."""
    text = source.strip()
    try:
        data = json.loads(text)
        return data if isinstance(data, dict | list) else None
    except ValueError:
        pass
    if text.startswith("<"):
        try:
            return _xml_tree(ET.fromstring(text))
        except ET.ParseError:
            return None
    return _csv_tree(text)


def _from_structure(tree: Any, source: str) -> Invoice | None:
    fields: dict[str, Any] = {}
    lines: list[dict[str, Any]] = []
    _collect(tree, fields, lines)
    total = _number(fields.get("total"))
    if not lines or total is None:
        return None
    text = {k: (str(v).strip() or None) if v is not None else None for k, v in fields.items()}
    items = [LineItem(description=str(li["description"]).strip(), quantity=_number(li["quantity"]),
                      unit_price=_number(li.get("unit_price")), amount=_number(li.get("amount")),
                      note=str(li["note"]).strip() if li.get("note") else None) for li in lines]
    return Invoice(
        invoice_number=text.get("invoice_number"), vendor=text.get("vendor"),
        invoice_date=_date(text.get("invoice_date")), due_date=_date(text.get("due_date")),
        due_date_as_written=text.get("due_date"),
        currency=(text.get("currency") or ("USD" if "$" in source else "")).upper() or None, line_items=items,
        subtotal=_number(text.get("subtotal")), tax=_number(text.get("tax")), shipping=_number(text.get("shipping")),
        total=total, payment_terms=text.get("payment_terms"), notes=text.get("notes"), revision=None, corrections=[],
    )


def extract(source: str) -> Invoice | None:
    """Read JSON, XML and CSV by field name, labelled text by pattern. None when no line items or total is found."""
    tree = _structured(source)
    if tree is not None:
        return _from_structure(tree, source)
    text = ocr_digits(source)
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
