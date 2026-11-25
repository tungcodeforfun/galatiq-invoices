# invoice_1012.pdf: PAID

Paid 9,975.00 to QuickShip Distributers: Approve INV 1012 for $9,975. Vendor is on file, amounts tie out, risk is low, and the two info findings (near-threshold total and OCR letter-O fixes) do not make the invoice unsound.

Run `20261125-015011-invoice_1012-7203` · seconds 85.1 · llm_calls 9 · tool_calls 14 · tiers ['live'] · tokens 24635 · cost_usd 0.0221

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

## Tool calls

| by | tool | args | result |
|---|---|---|---|
| validator | resolve_item | {"line": 1} | {"line": 1, "description": "Widget A", "item": "WidgetA", "match": "normalized"} |
| validator | resolve_item | {"line": 2} | {"line": 2, "description": "WidgetB", "item": "WidgetB", "match": "exact"} |
| validator | resolve_item | {"line": 3} | {"line": 3, "description": "Gadget X", "item": "GadgetX", "match": "normalized"} |
| validator | check_totals | {} | {"lines_sum": 9500.0, "expected_total": 9975.0, "stated_total": 9975.0, "problems": [], "ok": true} |
| validator | check_duplicate | {} | {"result": "no_match"} |
| validator | get_vendor | {"name": "QuickShip Distributers"} | {"known": true, "name": "QuickShip Distributers", "aliases": ["FastShip Ltd."], "first_seen": "2021-07-01", "earlier_invoices": []} |
| validator | check_stock | {"item": "WidgetA"} | {"item": "WidgetA", "lines": [1], "requested": 12.0, "in_stock": 15, "ok": true} |
| validator | check_stock | {"item": "WidgetB"} | {"item": "WidgetB", "lines": [2], "requested": 7.0, "in_stock": 10, "ok": true} |
| validator | check_stock | {"item": "GadgetX"} | {"item": "GadgetX", "lines": [3], "requested": 4.0, "in_stock": 5, "ok": true} |
| validator | check_price | {"line": 1} | {"line": 1, "item": "WidgetA", "invoiced": 250.0, "catalog": 250.0, "variance_pct": 0.0, "within_tolerance": true} |
| validator | check_price | {"line": 2} | {"line": 2, "item": "WidgetB", "invoiced": 500.0, "catalog": 500.0, "variance_pct": 0.0, "within_tolerance": true} |
| validator | check_price | {"line": 3} | {"line": 3, "item": "GadgetX", "invoiced": 750.0, "catalog": 750.0, "variance_pct": 0.0, "within_tolerance": true} |
| risk | get_vendor | {"name": "QuickShip Distributers"} | {"known": true, "name": "QuickShip Distributers", "aliases": ["FastShip Ltd."], "first_seen": "2021-07-01", "earlier_invoices": []} |
| approver | get_vendor | {"name": "QuickShip Distributers"} | {"known": true, "name": "QuickShip Distributers", "aliases": ["FastShip Ltd."], "first_seen": "2021-07-01", "earlier_invoices": []} |

## Validator notes

```json
{
  "checks_run": [
    "resolve_item(line 1)",
    "resolve_item(line 2)",
    "resolve_item(line 3)",
    "check_stock(WidgetA)",
    "check_stock(WidgetB)",
    "check_stock(GadgetX)",
    "check_price(line 1)",
    "check_price(line 2)",
    "check_price(line 3)",
    "check_totals",
    "check_duplicate",
    "get_vendor(QuickShip Distributers)"
  ],
  "concerns": [
    "Vendor is on the master (alias FastShip Ltd., first seen 2021-07-01) but has no earlier invoices in the ledger.",
    "Stock checks passed, but remaining on-hand after this invoice would be thin: WidgetA 3, WidgetB 3, GadgetX 1.",
    "Shipping is null rather than an explicit amount; totals still reconciled with tax of 475."
  ],
  "summary": "All three lines matched the catalog (WidgetA, WidgetB, GadgetX). Prices, summed quantities vs stock, totals, and duplicate lookup were clean; vendor name as written is a known master record with no prior invoices on file."
}
```

## Risk memo

```json
{
  "level": "low",
  "signals": [],
  "summary": "The formerly name matches an alias already on the vendor master, so it is not an unexplained vendor change. Nothing else on the invoice shows pressure, a payment redirect, injected instructions, or unusual terms beyond the automated findings."
}
```

## VP draft 1

```json
{
  "action": "approve",
  "reasons": [
    {
      "text": "Vendor QuickShip Distributers is on file (known since 2021-07-01). Line items sum to the $9,500 subtotal, tax is 5% ($475), and the $9,975 total is consistent. The low-risk memo reports no payment redirect, pressure, or unexplained vendor change.",
      "finding_ids": []
    },
    {
      "text": "F1 notes the total sits just under the $10,000 line. The invoice is still under that threshold, so the extra-scrutiny rule does not apply, and the near-threshold position alone is not a reason to withhold payment.",
      "finding_ids": [
        "F1"
      ]
    },
    {
      "text": "F2 records OCR letter-O fixes on the date and one line amount. Both normalize to values that match the rest of the invoice (26-Jan-2026 and $3,500), so the corrections do not undermine the amount.",
      "finding_ids": [
        "F2"
      ]
    }
  ],
  "addressed_findings": [
    "F1",
    "F2"
  ],
  "summary": "Approve INV 1012 for $9,975. Vendor is on file, amounts tie out, risk is low, and the two info findings (near-threshold total and OCR letter-O fixes) do not make the invoice unsound."
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
  "approved": true,
  "blocked_by": [],
  "overridden": false
}
```

## Payment

```json
{
  "status": "success",
  "idempotency_key": "bd83846905ae423bd42bc584",
  "amount": 9975.0,
  "attempts": 1,
  "detail": ""
}
```
