"""Code-only rules on the extracted invoice: extraction tracing, data integrity, currency, dates, injection screen."""

from __future__ import annotations

import re
from datetime import date

from invoice_agents.matching import text_key
from invoice_agents.policy import Policy
from invoice_agents.schema import Finding, Invoice
from invoice_agents.structured import total_from_lines

NUMBER = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?")
PLAIN_NUMBER = re.compile(r"\d+(?:\.\d+)?")
NET_TERMS = re.compile(r"net\s*(\d+)", re.IGNORECASE)
TERMS_SLACK_DAYS = 5

INSTRUCTION_LIKE = re.compile(
    r"ignore (?:all |any |the )?(?:previous|prior|above|earlier|your) (?:instructions|rules|checks)"
    r"|disregard (?:all |any |the )?(?:previous|prior|above|your)"
    r"|(?:system|developer) (?:message|prompt|override|instruction)"
    r"|\bas an ai\b|\bai (?:assistant|agent|model)\b|language model"
    r"|(?:you must|must be|please) (?:auto[- ]?)?approve|pre-?approved"
    r"|do not (?:flag|reject|check|verify)",
    re.IGNORECASE,
)


def ocr_digits(text: str) -> str:
    """Read letter O as zero where it sits next to a digit, as OCR often confuses them."""
    return re.sub(r"(?<=\d)[Oo]|[Oo](?=\d)", "0", text)


def numbers_in(text: str) -> set[float]:
    """Every number written in the text, raw and with OCR letter fixes, read with and without thousands commas."""
    found: list[str] = []
    for variant in (text, ocr_digits(text)):
        found += NUMBER.findall(variant) + PLAIN_NUMBER.findall(variant)
    return {float(n.replace(",", "")) for n in found}


def extraction_errors(invoice: Invoice, source: str, read_by_rules: bool = False) -> list[str]:
    """Every extracted value must trace to the document, bar a total the rules summed from a CSV's lines."""
    errors: list[str] = []
    written = numbers_in(source)
    source_key = text_key(ocr_digits(source))
    computed = read_by_rules and invoice.total == total_from_lines(invoice)
    checks: list[tuple[str, float | None]] = [
        ("subtotal", invoice.subtotal), ("tax", invoice.tax), ("shipping", invoice.shipping),
        ("total", None if computed else invoice.total),
    ]
    for n, li in enumerate(invoice.line_items, 1):
        checks += [(f"line {n} quantity", li.quantity), (f"line {n} unit_price", li.unit_price),
                   (f"line {n} amount", li.amount)]
        if text_key(li.description) not in source_key:
            errors.append(f"line {n} description '{li.description}' does not appear in the document")
    for name, value in checks:
        if value not in (None, 0) and abs(value) not in written:
            errors.append(f"{name} {value:g} does not appear in the document; use null if it is not written")
    for label, text in (("vendor", invoice.vendor), ("invoice_number", invoice.invoice_number)):
        if text and text_key(text) not in source_key:
            errors.append(f"{label} '{text}' does not appear in the document")
    for c in invoice.corrections:
        if text_key(c.as_written) not in text_key(source):
            errors.append(f"correction for {c.field}: '{c.as_written}' is not in the document")
    if not invoice.line_items and invoice.total is None:
        errors.append("no line items and no total were extracted")
    return errors


def _parse(value: str | None) -> date | None:
    try:
        return date.fromisoformat(value) if value else None
    except ValueError:
        return None


def _integrity_problems(invoice: Invoice, read_by_rules: bool) -> list[str]:
    problems = []
    if not (invoice.vendor or "").strip() and not read_by_rules:
        problems.append("vendor name is missing")
    if not (invoice.invoice_number or "").strip() and not read_by_rules:
        problems.append("invoice number is missing")
    if not invoice.line_items:
        problems.append("no line items")
    for n, li in enumerate(invoice.line_items, 1):
        if li.quantity is not None and li.quantity <= 0:
            problems.append(f"line {n} quantity is {li.quantity}")
        if li.unit_price is not None and li.unit_price < 0:
            problems.append(f"line {n} unit price is negative")
    if invoice.total is not None and invoice.total <= 0:
        problems.append(f"total is {invoice.total}")
    return problems


def _unread_values(invoice: Invoice, read_by_rules: bool) -> list[str]:
    """Blank values nothing could read: a number written in words, or a vendor only in a letterhead the rules skip."""
    unread = [f"the {name} on line {n}" for n, li in enumerate(invoice.line_items, 1)
              for name, blank in (("quantity", li.quantity is None),
                                  ("unit price", li.unit_price is None and li.amount is None)) if blank]
    unread += ["the total"] if invoice.total is None else []
    if read_by_rules:
        unread += ["the vendor name"] if not (invoice.vendor or "").strip() else []
        unread += ["the invoice number"] if not (invoice.invoice_number or "").strip() else []
    return unread


def _date_problem(invoice: Invoice) -> str | None:
    invoiced, due = _parse(invoice.invoice_date), _parse(invoice.due_date)
    if due is None:
        written = invoice.due_date_as_written
        return f"Due date '{written}' is not a calendar date" if written else "No due date"
    if invoiced and due <= invoiced:
        return f"Due {due} is not after the invoice date {invoiced}"
    net = NET_TERMS.search(invoice.payment_terms or "")
    if invoiced and net and abs((due - invoiced).days - int(net.group(1))) > TERMS_SLACK_DAYS:
        return f"Due {due} is {(due - invoiced).days} days after the invoice date, but terms say '{net.group(0)}'"
    return None


def invoice_findings(invoice: Invoice, source: str, policy: Policy, read_by_rules: bool = False) -> list[Finding]:
    """Findings that need only the invoice itself and policy: integrity, unread values, currency, dates, injection."""
    found: list[Finding] = []
    problems = _integrity_problems(invoice, read_by_rules)
    if problems:
        found.append(policy.finding("DATA_INTEGRITY", "; ".join(problems), "rules", subject="integrity"))
    unread = _unread_values(invoice, read_by_rules)
    if unread:
        listed = ", ".join(unread[:-1]) + " and " + unread[-1] if len(unread) > 1 else unread[0]
        found.append(policy.finding("UNREAD_VALUE", f"Could not read {listed} from the document. Enter the invoice "
                                    "by hand.", "rules", subject="unread"))

    currency = (invoice.currency or "USD").upper()
    if currency not in policy.currencies:
        found.append(policy.finding("CURRENCY", f"Invoice is in {currency}; we pay in {', '.join(policy.currencies)}",
                                    "rules", subject=currency, currency=currency))

    limit = policy.approval_threshold
    if invoice.total and limit * (1 - policy.near_threshold_pct / 100) <= invoice.total < limit:
        found.append(policy.finding("NEAR_THRESHOLD", f"Total {invoice.total:,.2f} sits just under the "
                                    f"{limit:,.0f} approval line", "rules", subject="threshold"))

    date_problem = _date_problem(invoice)
    if date_problem:
        found.append(policy.finding("DATE_ODDITY", date_problem, "rules", subject="due_date"))

    if invoice.corrections:
        fixes = "; ".join(f"{c.field}: '{c.as_written}' read as '{c.normalized}'" for c in invoice.corrections)
        found.append(policy.finding("OCR_CORRECTED", fixes, "rules", subject="corrections"))

    hits = sorted({m.group(0) for m in INSTRUCTION_LIKE.finditer(source)})
    if hits:
        found.append(policy.finding("FRAUD_SIGNALS", "Invoice text contains instructions aimed at the reviewer: "
                                    + ", ".join(f"'{h}'" for h in hits), "rules", subject="injection", quotes=hits))
    return found
