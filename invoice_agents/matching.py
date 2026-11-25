"""When two spellings are one thing: vendor names, catalog items, invoice numbers and invoice content."""

from __future__ import annotations

import hashlib
import json
import re
from difflib import SequenceMatcher
from typing import Any

from invoice_agents.schema import Invoice

NEAR_MISS = 0.8


def text_key(text: str | None) -> str:
    """Lowercase alphanumerics only: 'Widget A' and 'widget-a' compare equal."""
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


def item_key(description: str) -> str:
    """Key for catalog matching: drops parenthetical notes such as '(rush order)'."""
    return text_key(re.sub(r"\(.*?\)", "", description))


def number_key(number: str | None) -> str:
    """Invoice number without an 'INV' prefix or punctuation: 'INV-1002', 'INV 1002' and '1002' are one key."""
    return re.sub(r"^inv(oice)?", "", text_key(number))


def invoice_key(vendor: str | None, number: str | None) -> str:
    """One key per vendor and invoice number, however either is written."""
    return f"{text_key(vendor)}|{number_key(number)}"


def resolve_item(description: str, catalog: dict[str, Any]) -> tuple[str | None, str]:
    """Map a line description to a catalog item. Returns (item, 'exact' | 'normalized' | 'none'); never guesses."""
    if description in catalog:
        return description, "exact"
    key = item_key(description)
    for item in catalog:
        if text_key(item) == key:
            return item, "normalized"
    return None, "none"


def closest_items(description: str, catalog: dict[str, Any]) -> list[str]:
    """Nearest catalog items to an unmatched name, all tied for nearest: a hint for people, never a match."""
    scores = {item: SequenceMatcher(None, item_key(description), text_key(item)).ratio() for item in catalog}
    best = max(scores.values(), default=0.0)
    return [item for item, score in scores.items() if score == best >= NEAR_MISS]


def content_hash(invoice: Invoice, catalog: dict[str, Any]) -> str:
    """Fingerprint of what is being billed (vendor, lines, total), ignoring the invoice number and layout."""
    lines = sorted(
        (resolve_item(li.description, catalog)[0] or item_key(li.description), li.quantity, li.unit_price)
        for li in invoice.line_items
    )
    payload = [text_key(invoice.vendor), [[i, float(q or 0), float(p or 0)] for i, q, p in lines], invoice.total]
    return hashlib.sha256(json.dumps(payload).encode()).hexdigest()[:16]
