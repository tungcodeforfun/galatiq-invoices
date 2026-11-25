"""Reads JSON, XML and CSV invoices by their field names, for degraded mode when no model is available."""

from __future__ import annotations

import csv
import io
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any

from invoice_agents.matching import text_key
from invoice_agents.schema import Invoice, LineItem

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


def to_number(raw: Any) -> float | None:
    """A number from text such as '$1,250.00'; None when there is none."""
    try:
        return float(re.sub(r"[^\d.\-]", "", str(raw))) if raw not in (None, "") else None
    except ValueError:
        return None


def to_date(raw: Any) -> str | None:
    """An ISO date from the common written forms; None when it is not a date."""
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(str(raw or "").strip(), fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _key(name: Any) -> str:
    return text_key(re.sub(r"\(.*?\)", "", str(name)))


def _field(names: dict[str, set[str]], key: str) -> str | None:
    return next((field for field, aliases in names.items() if key in aliases), None)


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


def _parse(source: str) -> Any:
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


def total_from_lines(invoice: Invoice) -> float | None:
    """Lines (each as written, or quantity times unit price) plus tax and shipping; None if a line has neither."""
    amounts = [li.amount if li.amount is not None else
               li.quantity * li.unit_price if li.quantity is not None and li.unit_price is not None else None
               for li in invoice.line_items]
    if not amounts or None in amounts:
        return None
    return round(sum(a for a in amounts if a is not None) + (invoice.tax or 0) + (invoice.shipping or 0), 2)


def read_structured(source: str) -> Invoice | None:
    """The invoice in a JSON, XML or CSV file, a CSV without a total row totalled from its lines; else None."""
    tree = _parse(source)
    fields: dict[str, Any] = {}
    lines: list[dict[str, Any]] = []
    _collect(tree, fields, lines)
    if not lines:
        return None
    text = {k: (str(v).strip() or None) if v is not None else None for k, v in fields.items()}
    items = [LineItem(description=str(li["description"]).strip(), quantity=to_number(li["quantity"]),
                      unit_price=to_number(li.get("unit_price")), amount=to_number(li.get("amount")),
                      note=str(li["note"]).strip() if li.get("note") else None) for li in lines]
    invoice = Invoice(
        invoice_number=text.get("invoice_number"), vendor=text.get("vendor"),
        invoice_date=to_date(text.get("invoice_date")), due_date=to_date(text.get("due_date")),
        due_date_as_written=text.get("due_date"),
        currency=(text.get("currency") or ("USD" if "$" in source else "")).upper() or None, line_items=items,
        subtotal=to_number(text.get("subtotal")), tax=to_number(text.get("tax")),
        shipping=to_number(text.get("shipping")), total=to_number(fields.get("total")),
        payment_terms=text.get("payment_terms"), notes=text.get("notes"), revision=None, corrections=[],
    )
    if invoice.total is None and not source.lstrip().startswith(("{", "[", "<")):
        invoice.total = total_from_lines(invoice)
    return invoice if invoice.total is not None else None
