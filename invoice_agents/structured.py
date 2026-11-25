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
CONTACT_NAMES = {"address", "street", "city", "state", "zip", "zipcode", "postcode", "postalcode", "country", "email",
                 "phone", "fax", "website", "taxid", "vatid", "vatnumber", "contact"}
PROSE_NAMES = FIELD_NAMES["notes"] | LINE_NAMES["note"]


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


def read_structured(source: str) -> Invoice | None:
    """The invoice in a JSON, XML or CSV document; None if it is none of them or has no line items or total."""
    tree = _parse(source)
    fields: dict[str, Any] = {}
    lines: list[dict[str, Any]] = []
    _collect(tree, fields, lines)
    total = to_number(fields.get("total"))
    if not lines or total is None:
        return None
    text = {k: (str(v).strip() or None) if v is not None else None for k, v in fields.items()}
    items = [LineItem(description=str(li["description"]).strip(), quantity=to_number(li["quantity"]),
                      unit_price=to_number(li.get("unit_price")), amount=to_number(li.get("amount")),
                      note=str(li["note"]).strip() if li.get("note") else None) for li in lines]
    return Invoice(
        invoice_number=text.get("invoice_number"), vendor=text.get("vendor"),
        invoice_date=to_date(text.get("invoice_date")), due_date=to_date(text.get("due_date")),
        due_date_as_written=text.get("due_date"),
        currency=(text.get("currency") or ("USD" if "$" in source else "")).upper() or None, line_items=items,
        subtotal=to_number(text.get("subtotal")), tax=to_number(text.get("tax")),
        shipping=to_number(text.get("shipping")), total=total, payment_terms=text.get("payment_terms"),
        notes=text.get("notes"), revision=None, corrections=[],
    )


def _prose(key: str, value: Any, in_line: bool, party: bool) -> bool:
    """Notes are free text; so is any value of two or more words under a field the reader does not use."""
    text = str(value).strip() if value is not None else ""
    if not text or key in PROSE_NAMES:
        return bool(text)
    read = _field(FIELD_NAMES, key) or (in_line and _field(LINE_NAMES, key)) or (party and key in CONTACT_NAMES)
    return not read and len(text.split()) > 1


def _tree_text(node: Any, key: str = "", in_line: bool = False, party: bool = False) -> list[str]:
    if isinstance(node, list):
        return [t for child in node for t in _tree_text(child, key, in_line, party)]
    if isinstance(node, dict):
        line = _line(node) is not None
        return [t for k, v in node.items() for t in _tree_text(
            v, _key(k), line, party or _key(k) in OTHER_PARTIES or _field(FIELD_NAMES, _key(k)) == "vendor")]
    return [str(node).strip()] if _prose(key, node, in_line, party) else []


def _xml_text(source: str) -> list[str]:
    """Text the tree drops: comments, processing instructions, text beside child elements, and prose attributes."""
    root = ET.fromstring(source.strip(), ET.XMLParser(target=ET.TreeBuilder(insert_comments=True, insert_pis=True)))
    found: list[str] = []
    for element in root.iter():
        own = (element.text or "").strip() if len(element) or not isinstance(element.tag, str) else ""
        found += [t for t in (own, (element.tail or "").strip()) if t]
        found += [v for v in element.attrib.values() if len(v.split()) > 1]
    return found


def _csv_text(source: str) -> list[str]:
    """Rows other than line items that carry more than a label the reader uses and its one value."""
    rows = [r for r in csv.reader(io.StringIO(source)) if any(c.strip() for c in r)]
    header = rows[0] if len(rows[0]) > 2 else []
    found = []
    for row in rows[1:] if header else rows:
        cells = [c.strip() for c in row if c.strip()]
        label = _key(cells[0])
        if (header and _line(dict(zip(header, row, strict=True)))) or label == "field":
            continue
        known = _field(FIELD_NAMES, label) or _field(LINE_NAMES, label)
        if len(cells) > 2 or (label in PROSE_NAMES and len(cells) > 1) or (not known and len(cells[0].split()) > 1):
            found.append(" ".join(cells))
    return found


def free_text(source: str) -> list[str] | None:
    """Free text in a JSON, XML or CSV document that no rule reads; None if the document is none of them."""
    tree = _parse(source)
    if tree is None:
        return None
    found = _tree_text(tree)
    text = source.strip()
    if text.startswith("<"):
        found += _xml_text(text)
    elif not text.startswith(("{", "[")):
        found += _csv_text(text)
    return list(dict.fromkeys(found))
