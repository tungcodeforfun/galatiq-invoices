"""Tool calls in plain words for the dashboard: what was checked, and what the tool found."""

from __future__ import annotations

from typing import Any

from invoice_agents.fallback import STEP_NAMES


def _money(value: Any) -> str:
    return f"{value:,.2f}" if isinstance(value, int | float) else "—"


def _resolve(r: dict[str, Any]) -> str:
    if r.get("item") is None:
        hint = f"; did you mean {' or '.join(r['suggestions'])}?" if r.get("suggestions") else ""
        return f"'{r['description']}' is not in the catalog{hint}"
    return f"'{r['description']}' is {r['item']}"


def _stock(r: dict[str, Any]) -> str:
    lines = ", ".join(map(str, r["lines"]))
    over = "" if r["ok"] else ": more than we hold"
    return f"{r['requested']:g} requested (line{'s' * (len(r['lines']) > 1)} {lines}), {r['in_stock']} in stock{over}"


def _price(r: dict[str, Any]) -> str:
    if not r.get("checked", True):
        return "no catalog price to compare"
    verdict = "within tolerance" if r["within_tolerance"] else "outside tolerance"
    return f"{_money(r['invoiced'])} vs catalog {_money(r['catalog'])} ({r['variance_pct']:+g}%): {verdict}"


def _totals(r: dict[str, Any]) -> str:
    if r["ok"]:
        return f"lines + tax + shipping = {_money(r['expected_total'])}, as stated"
    return "; ".join(r["problems"])


def _duplicate(r: dict[str, Any]) -> str:
    if r["result"] == "duplicate":
        return f"same bill as {r['of']} ({r['prior_status'].lower()})"
    if r["result"] == "revision_conflict":
        return f"this number was {r['prior_status'].lower()} at {_money(r['prior_total'])}; now {r['delta']:+,.2f}"
    return "no earlier invoice matches"


def _vendor(r: dict[str, Any]) -> str:
    if not r.get("known"):
        return r.get("note") or "not in the vendor master"
    earlier = len(r.get("earlier_invoices") or [])
    return f"on file since {r['first_seen']}, {earlier} earlier invoice{'s' if earlier != 1 else ''}"


RESULTS = {"resolve_item": _resolve, "check_stock": _stock, "check_price": _price, "check_totals": _totals,
           "check_duplicate": _duplicate, "get_vendor": _vendor}
NAMES = {"resolve_item": "Match item", "check_stock": "Stock", "check_price": "Price", "check_totals": "Totals",
         "check_duplicate": "Duplicates", "get_vendor": "Vendor"}
CALLERS = STEP_NAMES | {"coverage": "Coverage check"}


def call_in_words(call: dict[str, Any]) -> dict[str, str]:
    """One tool call as a table row: who called it, which check, on what, and what it found."""
    args, result = call["args"], call["result"]
    subject = (f"line {args['line']}" if "line" in args else args.get("item") or args.get("name") or "whole invoice")
    found = f"error: {result['error']}" if "error" in result else RESULTS.get(call["tool"], str)(result)
    return {"By": CALLERS.get(call["by"], call["by"]), "Check": NAMES.get(call["tool"], call["tool"]),
            "On": subject, "Found": found}
