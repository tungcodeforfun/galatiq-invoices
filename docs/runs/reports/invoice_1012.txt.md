# invoice_1012.txt: REJECTED (void)

This invoice is voided because F3 identifies it as a duplicate of INV 1012, already PAID, with the same vendor, lines, and total. F1 (total 9,975.00 just under the 10,000 approval line) and F2 (OCR normalizations of the invoice date and a line amount) are informational and do not repair the duplicate. A duplicate must not be resubmitted, so the disposition is void.

Run `20261125-015137-invoice_1012-bb8b` · seconds 113.7 · llm_calls 9 · tool_calls 13 · tiers ['live'] · tokens 24679 · cost_usd 0.029

## Extracted invoice

| field | value |
|---|---|
| invoice_number | INV 1012 |
| vendor | QuickShip Distributers |
| invoice_date | 2026-01-26 |
| due_date | 2026-02-25 |
| due_date_as_written | 25-Feb-2026 |
| currency | USD |
| subtotal | 9500.0 |
| tax | 475.0 |
| shipping | None |
| total | 9975.0 |
| payment_terms | Net 30 |
| notes | Ref PO-20260115. Deliver to warehouse dock B. Contact Jim at ext 4421 with questions. |
| revision | None |

| # | description | qty | unit price | amount | note |
|---|---|---|---|---|---|
| 1 | Widget A | 12.0 | 250.0 | 3000.0 |  |
| 2 | WidgetB | 7.0 | 500.0 | 3500.0 |  |
| 3 | Gadget X | 4.0 | 750.0 | 3000.0 |  |

## Findings

| id | code | severity | message | source |
|---|---|---|---|---|
| F1 | NEAR_THRESHOLD | info | Total 9,975.00 sits just under the 10,000 approval line | rules |
| F2 | OCR_CORRECTED | info | invoice_date: '26-Jan-2O26' read as '2026-01-26'; line_items[1].amount: '$3,500.O0' read as '3500.00' | rules |
| F3 | DUPLICATE | reject | Same vendor, lines and total as INV 1012 (PAID) | check_duplicate |

## Tool calls

| by | tool | args | result |
|---|---|---|---|
| validator | resolve_item | {"line": 1} | {"line": 1, "description": "Widget A", "item": "WidgetA", "match": "normalized"} |
| validator | resolve_item | {"line": 2} | {"line": 2, "description": "WidgetB", "item": "WidgetB", "match": "exact"} |
| validator | resolve_item | {"line": 3} | {"line": 3, "description": "Gadget X", "item": "GadgetX", "match": "normalized"} |
| validator | check_totals | {} | {"lines_sum": 9500.0, "expected_total": 9975.0, "stated_total": 9975.0, "problems": [], "ok": true} |
| validator | check_duplicate | {} | {"result": "duplicate", "of": "INV 1012", "prior_status": "PAID"} |
| validator | get_vendor | {"name": "QuickShip Distributers"} | {"known": true, "name": "QuickShip Distributers", "aliases": ["FastShip Ltd."], "first_seen": "2021-07-01", "earlier_invoices": [{"number": "INV 1012", "total": |
| validator | check_stock | {"item": "WidgetA"} | {"item": "WidgetA", "lines": [1], "requested": 12.0, "in_stock": 15, "ok": true} |
| validator | check_stock | {"item": "WidgetB"} | {"item": "WidgetB", "lines": [2], "requested": 7.0, "in_stock": 10, "ok": true} |
| validator | check_stock | {"item": "GadgetX"} | {"item": "GadgetX", "lines": [3], "requested": 4.0, "in_stock": 5, "ok": true} |
| validator | check_price | {"line": 1} | {"line": 1, "item": "WidgetA", "invoiced": 250.0, "catalog": 250.0, "variance_pct": 0.0, "within_tolerance": true} |
| validator | check_price | {"line": 2} | {"line": 2, "item": "WidgetB", "invoiced": 500.0, "catalog": 500.0, "variance_pct": 0.0, "within_tolerance": true} |
| validator | check_price | {"line": 3} | {"line": 3, "item": "GadgetX", "invoiced": 750.0, "catalog": 750.0, "variance_pct": 0.0, "within_tolerance": true} |
| risk | get_vendor | {"name": "QuickShip Distributers"} | {"known": true, "name": "QuickShip Distributers", "aliases": ["FastShip Ltd."], "first_seen": "2021-07-01", "earlier_invoices": [{"number": "INV 1012", "total": |

## Validator notes

```json
{
  "checks_run": [
    "resolve_item(1)",
    "resolve_item(2)",
    "resolve_item(3)",
    "check_stock(WidgetA)",
    "check_stock(WidgetB)",
    "check_stock(GadgetX)",
    "check_price(1)",
    "check_price(2)",
    "check_price(3)",
    "check_totals",
    "check_duplicate",
    "get_vendor(QuickShip Distributers)"
  ],
  "concerns": [
    "Vendor master lists an alias, FastShip Ltd., which this invoice does not use; payment identity was not otherwise distinguished from the canonical name.",
    "Notes cite PO-20260115 and an internal contact; neither was verified by these tools. Shipping is blank rather than an explicit zero, though totals still reconciled."
  ],
  "summary": "All three lines matched the catalog (WidgetA, WidgetB, GadgetX). Stock, unit prices, and stated totals checked out, but check_duplicate and the vendor ledger both show INV 1012 for $9975.00 already PAID, so this looks like a resubmission of a paid invoice."
}
```

## Risk memo

```json
{
  "level": "low",
  "signals": [],
  "summary": "No pressure language, payment redirection, instruction injection, or unexplained vendor change appears in the invoice text. The formerly name is already an alias on the vendor master, so there is nothing beyond the automated findings."
}
```

## VP draft 1

```json
{
  "action": "reject",
  "reasons": [
    {
      "text": "F3 is a reject-severity duplicate: this invoice matches vendor, lines, and total of INV 1012, which is already PAID. The payment gate blocks it; approving would miss a clear duplicate.",
      "finding_ids": [
        "F3"
      ]
    },
    {
      "text": "F1 notes the total of 9,975.00 sits just under the 10,000 line. That is informational only and does not change the duplicate block. The invoice is under 10,000, so the over-threshold extra-scrutiny rule does not apply.",
      "finding_ids": [
        "F1"
      ]
    },
    {
      "text": "F2 records routine OCR normalizations (date '26-Jan-2O26' and line amount '$3,500.O0'). Those corrections are consistent with the extracted amounts and do not repair the duplicate.",
      "finding_ids": [
        "F2"
      ]
    },
    {
      "text": "The risk memo is low, with no pressure language, payment redirection, or unexplained vendor change. A low memo does not outweigh F3.",
      "finding_ids": [
        "F3"
      ]
    }
  ],
  "addressed_findings": [
    "F1",
    "F2",
    "F3"
  ],
  "summary": "Reject. INV 1012 is a duplicate of an invoice already paid for the same vendor, lines, and total (F3). Info findings and the low risk memo do not override that block."
}
```

## Critique 1

```json
{
  "verdict": "accept",
  "objections": []
}
```

## Policy gate

```json
{
  "approved": false,
  "blocked_by": [
    "approver rejected"
  ],
  "overridden": false
}
```

## Resolution

```json
{
  "disposition": "void",
  "reasoning": "This invoice is voided because F3 identifies it as a duplicate of INV 1012, already PAID, with the same vendor, lines, and total. F1 (total 9,975.00 just under the 10,000 approval line) and F2 (OCR normalizations of the invoice date and a line amount) are informational and do not repair the duplicate. A duplicate must not be resubmitted, so the disposition is void.",
  "vendor_reply": null
}
```
