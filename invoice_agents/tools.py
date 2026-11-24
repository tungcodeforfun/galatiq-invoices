"""Deterministic checks the agents call as tools. Every number and every finding here comes from code."""

from __future__ import annotations

import hashlib
import json
import re
from decimal import Decimal
from typing import Any

from invoice_agents.db import Store
from invoice_agents.policy import Policy
from invoice_agents.schema import Finding, Invoice

COUNTED_STATUSES = ("PAID", "REJECTED")


def text_key(text: str | None) -> str:
    """Lowercase alphanumerics only: 'Widget A' and 'widget-a' compare equal."""
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


def item_key(description: str) -> str:
    """Key for catalog matching: drops parenthetical notes such as '(rush order)'."""
    return text_key(re.sub(r"\(.*?\)", "", description))


def number_key(number: str | None) -> str:
    """Invoice number without an 'INV' prefix or punctuation: 'INV-1002', 'INV 1002' and '1002' are one key."""
    return re.sub(r"^inv(oice)?", "", text_key(number))


def money(value: float | None) -> Decimal:
    """Exact decimal for money arithmetic."""
    return Decimal(str(value or 0))


def resolve_item(description: str, catalog: dict[str, Any]) -> tuple[str | None, str]:
    """Map a line description to a catalog item. Returns (item, 'exact' | 'normalized' | 'none'); never guesses."""
    if description in catalog:
        return description, "exact"
    key = item_key(description)
    for item in catalog:
        if text_key(item) == key:
            return item, "normalized"
    return None, "none"


def content_hash(invoice: Invoice, catalog: dict[str, Any]) -> str:
    """Fingerprint of what is being billed (vendor, lines, total), ignoring the invoice number and layout."""
    lines = sorted(
        (resolve_item(li.description, catalog)[0] or item_key(li.description), li.quantity, li.unit_price)
        for li in invoice.line_items
    )
    payload = [text_key(invoice.vendor), [[i, float(q or 0), float(p or 0)] for i, q, p in lines], invoice.total]
    return hashlib.sha256(json.dumps(payload).encode()).hexdigest()[:16]


TOOL_SPECS: dict[str, dict[str, Any]] = {
    "resolve_item": {
        "description": "Match one invoice line to the inventory catalog. Returns the catalog item or no match.",
        "parameters": {"line": {"type": "integer", "description": "Line number, starting at 1"}},
    },
    "check_stock": {
        "description": "Sum the quantity of a catalog item across every line of this invoice and compare it "
        "with stock on hand.",
        "parameters": {"item": {"type": "string", "description": "Catalog item name, e.g. 'WidgetA'"}},
    },
    "check_price": {
        "description": "Compare one line's unit price with the catalog price.",
        "parameters": {"line": {"type": "integer", "description": "Line number, starting at 1"}},
    },
    "check_totals": {
        "description": "Recompute line amounts, subtotal and total (lines + tax + shipping) and compare them "
        "with what the invoice states.",
        "parameters": {},
    },
    "check_duplicate": {
        "description": "Look this invoice up in the ledger of processed invoices: exact resubmission, "
        "same content under another number, or a changed revision of an invoice already decided.",
        "parameters": {},
    },
    "get_vendor": {
        "description": "Look up a vendor in the vendor master (aliases, first seen) and list its earlier invoices.",
        "parameters": {"name": {"type": "string", "description": "Vendor name as written on the invoice"}},
    },
}


class ToolBox:
    """The tools for one invoice. Collects findings and records which checks ran, for the coverage loop."""

    def __init__(self, invoice: Invoice, store: Store, policy: Policy):
        self.invoice = invoice
        self.store = store
        self.policy = policy
        self.catalog = store.catalog()
        self.findings: dict[tuple[str, str], Finding] = {}
        self.calls: list[dict[str, Any]] = []

    def specs(self, names: list[str]) -> list[dict[str, Any]]:
        """OpenAI-style function specs for the named tools."""
        return [
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": TOOL_SPECS[name]["description"],
                    "parameters": {
                        "type": "object",
                        "properties": TOOL_SPECS[name]["parameters"],
                        "required": list(TOOL_SPECS[name]["parameters"]),
                        "additionalProperties": False,
                    },
                },
            }
            for name in names
        ]

    def call(self, name: str, args: dict[str, Any], by: str = "agent") -> dict[str, Any]:
        """Run one tool by name and log the call."""
        if name not in TOOL_SPECS:
            result: dict[str, Any] = {"error": f"unknown tool {name}"}
        else:
            try:
                result = getattr(self, name)(**args)
            except (TypeError, ValueError, IndexError) as exc:
                result = {"error": str(exc)}
        self.calls.append({"tool": name, "args": args, "by": by, "result": result})
        return result

    def _add(self, finding: Finding) -> None:
        self.findings.setdefault((finding.code, finding.subject), finding)

    def _line(self, line: int):
        if not 1 <= line <= len(self.invoice.line_items):
            raise IndexError(f"line must be between 1 and {len(self.invoice.line_items)}")
        return self.invoice.line_items[line - 1]

    def resolve_item(self, line: int) -> dict[str, Any]:
        """Catalog match for one line; an unmatched line is an UNKNOWN_ITEM finding."""
        description = self._line(line).description
        item, match = resolve_item(description, self.catalog)
        if item is None:
            self._add(
                self.policy.finding(
                    "UNKNOWN_ITEM", f"'{description}' is not in the inventory catalog", "resolve_item",
                    subject=description, line=line,
                )
            )
        return {"line": line, "description": description, "item": item, "match": match}

    def check_stock(self, item: str) -> dict[str, Any]:
        """Total requested quantity of one item across all lines versus stock on hand."""
        resolved, _ = resolve_item(item, self.catalog)
        if resolved is None:
            return {"error": f"'{item}' is not a catalog item"}
        lines = [
            (n, li.quantity or 0)
            for n, li in enumerate(self.invoice.line_items, 1)
            if resolve_item(li.description, self.catalog)[0] == resolved
        ]
        requested = sum(q for _, q in lines)
        stock = self.catalog[resolved]["stock"]
        if requested > stock:
            self._add(
                self.policy.finding(
                    "STOCK_EXCEEDED", f"{resolved}: {requested:g} requested across {len(lines)} line(s), "
                    f"{stock} in stock", "check_stock", subject=resolved, requested=requested, in_stock=stock,
                )
            )
        if stock == 0:
            self._add(
                self.policy.finding(
                    "FRAUD_SIGNALS", f"{resolved} is a catalog item we hold none of and never price",
                    "check_stock", subject=f"zero-stock:{resolved}", item=resolved,
                )
            )
        return {"item": resolved, "lines": [n for n, _ in lines], "requested": requested, "in_stock": stock,
                "ok": requested <= stock}

    def check_price(self, line: int) -> dict[str, Any]:
        """One line's unit price against the catalog price, with the policy tolerance."""
        li = self._line(line)
        item, _ = resolve_item(li.description, self.catalog)
        catalog_price = self.catalog[item]["unit_price"] if item else None
        if catalog_price is None or li.unit_price is None:
            return {"line": line, "item": item, "checked": False, "reason": "no catalog price or no unit price"}
        variance = (li.unit_price - catalog_price) / catalog_price * 100
        within = abs(variance) <= self.policy.price_tolerance_pct
        if not within:
            self._add(
                self.policy.finding(
                    "PRICE_VARIANCE", f"Line {line} {item} at {li.unit_price:,.2f} vs catalog "
                    f"{catalog_price:,.2f} ({variance:+.0f}%)", "check_price", subject=f"line {line}",
                    line=line, invoiced=li.unit_price, catalog=catalog_price, variance_pct=round(variance, 1),
                )
            )
        return {"line": line, "item": item, "invoiced": li.unit_price, "catalog": catalog_price,
                "variance_pct": round(variance, 1), "within_tolerance": within}

    def check_totals(self) -> dict[str, Any]:
        """Recompute every line, the subtotal and the total; each difference beyond tolerance is a finding."""
        inv, tol = self.invoice, Decimal(str(self.policy.total_tolerance))
        problems: list[str] = []
        lines_sum = Decimal(0)
        for n, li in enumerate(inv.line_items, 1):
            computed = money(li.quantity) * money(li.unit_price)
            if li.amount is not None and li.quantity is not None and li.unit_price is not None:
                if abs(computed - money(li.amount)) > tol:
                    problems.append(f"line {n}: {li.quantity:g} x {li.unit_price:,.2f} = {computed:,.2f}, "
                                    f"invoice says {li.amount:,.2f}")
            lines_sum += money(li.amount) if li.amount is not None else computed
        if inv.subtotal is not None and abs(lines_sum - money(inv.subtotal)) > tol:
            problems.append(f"lines add up to {lines_sum:,.2f}, subtotal says {inv.subtotal:,.2f}")
        expected = lines_sum + money(inv.tax) + money(inv.shipping)
        difference = money(inv.total) - expected if inv.total is not None else None
        if difference is not None and abs(difference) > tol:
            problems.append(f"lines + tax + shipping = {expected:,.2f}, total says {inv.total:,.2f} "
                            f"({difference:+,.2f})")
        if problems:
            self._add(self.policy.finding("TOTAL_MISMATCH", "; ".join(problems), "check_totals",
                                          subject="totals", difference=float(difference or 0)))
        return {"lines_sum": float(lines_sum), "expected_total": float(expected), "stated_total": inv.total,
                "problems": problems, "ok": not problems}

    def check_duplicate(self) -> dict[str, Any]:
        """Exact or content duplicates void the invoice; a changed invoice under a decided number is a conflict."""
        inv = self.invoice
        nk, vk, ch = number_key(inv.invoice_number), text_key(inv.vendor), content_hash(inv, self.catalog)
        prior = [r for r in self.store.related_invoices(nk, vk, ch) if r["status"] in COUNTED_STATUSES]
        same_content = [r for r in prior if r["content_hash"] == ch]
        same_number = [r for r in prior if nk and r["number_key"] == nk and r["vendor_key"] == vk]
        if same_content:
            first = same_content[0]
            self._add(
                self.policy.finding(
                    "DUPLICATE", f"Same vendor, lines and total as {first['number']} ({first['status']})",
                    "check_duplicate", subject="duplicate", prior_number=first["number"],
                    prior_status=first["status"], prior_file=first["source_file"],
                )
            )
            return {"result": "duplicate", "of": first["number"], "prior_status": first["status"]}
        if same_number:
            first = same_number[-1]
            delta = round((inv.total or 0) - (first["total"] or 0), 2)
            self._add(
                self.policy.finding(
                    "REVISION_CONFLICT", f"{first['number']} was already {first['status']} at "
                    f"{first['total']:,.2f}; this version totals {inv.total or 0:,.2f} ({delta:+,.2f})",
                    "check_duplicate", subject="revision", prior_total=first["total"],
                    prior_status=first["status"], delta=delta,
                )
            )
            return {"result": "revision_conflict", "prior_total": first["total"],
                    "prior_status": first["status"], "delta": delta}
        return {"result": "no_match"}

    def get_vendor(self, name: str) -> dict[str, Any]:
        """Vendor master record and earlier invoices; an unknown vendor is noted, never blocked."""
        key = text_key(name)
        match = next(
            (v for v in self.store.vendors() if key in {text_key(v["name"]), *map(text_key, v["aliases"])}), None
        )
        history = [
            {"number": r["number"], "total": r["total"], "status": r["status"], "disposition": r["disposition"]}
            for r in self.store.related_invoices("", key, "")
            if r["vendor_key"] == key
        ]
        if match is None:
            self._add(self.policy.finding("NEW_VENDOR", f"'{name}' is not in the vendor master", "get_vendor",
                                          subject=key))
            return {"known": False, "name": name, "earlier_invoices": history}
        return {"known": True, "name": match["name"], "aliases": match["aliases"],
                "first_seen": match["first_seen"], "earlier_invoices": history}

    def missing_checks(self) -> list[tuple[str, dict[str, Any]]]:
        """Checks the coverage rule requires that have not run yet."""
        ran = {(c["tool"], json.dumps(c["args"], sort_keys=True)) for c in self.calls if "error" not in c["result"]}
        required: list[tuple[str, dict[str, Any]]] = []
        items: list[str] = []
        for n, li in enumerate(self.invoice.line_items, 1):
            required.append(("resolve_item", {"line": n}))
            item, _ = resolve_item(li.description, self.catalog)
            if item:
                required.append(("check_price", {"line": n}))
                if item not in items:
                    items.append(item)
        required += [("check_stock", {"item": i}) for i in items]
        required += [("check_totals", {}), ("check_duplicate", {}), ("get_vendor", {"name": self.invoice.vendor or ""})]
        done_stock = {
            resolve_item(c["args"].get("item", ""), self.catalog)[0] for c in self.calls if c["tool"] == "check_stock"
        }
        return [
            (tool, args) for tool, args in required
            if (tool, json.dumps(args, sort_keys=True)) not in ran
            and not (tool == "check_stock" and args["item"] in done_stock)
            and not (tool == "get_vendor" and any(c["tool"] == "get_vendor" for c in self.calls))
        ]

    def run_missing(self) -> list[tuple[str, dict[str, Any]]]:
        """Run every check the agent skipped, in code, and return what had to be run."""
        missing = self.missing_checks()
        for tool, args in missing:
            self.call(tool, args, by="coverage")
        return missing

    def finding_list(self) -> list[Finding]:
        """Findings collected so far, in the order they were raised."""
        return list(self.findings.values())
