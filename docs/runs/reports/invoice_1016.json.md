# invoice_1016.json: REJECTED (return_to_vendor)

INV-1016 is rejected under F1 because line item WidgetC is not in the inventory catalog. Unknown items can be corrected and resubmitted, so policy requires return_to_vendor rather than void. The vendor must identify the intended catalog item and resubmit a corrected invoice before payment can proceed.

Run `20261125-035710-invoice_1016-b3bc` · seconds 44.3 · llm_calls 9 · tool_calls 11 · tiers ['live'] · tokens 23393 · cost_usd 0.0171

## Extracted invoice

| field | value |
|---|---|
| invoice_number | INV-1016 |
| vendor | Widgets Inc. |
| invoice_date | 2026-01-27 |
| due_date | 2026-02-27 |
| due_date_as_written | 2026-02-27 |
| currency | USD |
| subtotal | 3050.0 |
| tax | 183.0 |
| shipping | None |
| total | 3233.0 |
| payment_terms | Net 30 |
| notes | None |
| revision | None |

| # | description | qty | unit price | amount | note |
|---|---|---|---|---|---|
| 1 | WidgetA | 4.0 | 250.0 | 1000.0 |  |
| 2 | WidgetB | 2.0 | 500.0 | 1000.0 |  |
| 3 | WidgetC | 3.0 | 350.0 | 1050.0 |  |

## Findings

| id | code | severity | message | source |
|---|---|---|---|---|
| F1 | UNKNOWN_ITEM | reject | 'WidgetC' is not in the inventory catalog; did you mean WidgetA or WidgetB? | resolve_item |

## Tool calls

| by | tool | args | result |
|---|---|---|---|
| validator | resolve_item | {"line": 1} | {"line": 1, "description": "WidgetA", "item": "WidgetA", "match": "exact"} |
| validator | resolve_item | {"line": 2} | {"line": 2, "description": "WidgetB", "item": "WidgetB", "match": "exact"} |
| validator | resolve_item | {"line": 3} | {"line": 3, "description": "WidgetC", "item": null, "match": "none", "suggestions": ["WidgetA", "WidgetB"]} |
| validator | check_totals | {} | {"lines_sum": 3050.0, "expected_total": 3233.0, "stated_total": 3233.0, "problems": [], "ok": true} |
| validator | check_duplicate | {} | {"result": "no_match"} |
| validator | get_vendor | {"name": "Widgets Inc."} | {"known": true, "name": "Widgets Inc.", "aliases": [], "first_seen": "2023-03-01", "earlier_invoices": [{"number": "INV-1001", "total": 5000.0, "status": "PAID" |
| validator | check_stock | {"item": "WidgetA"} | {"item": "WidgetA", "lines": [1], "requested": 4.0, "in_stock": 15, "ok": true} |
| validator | check_stock | {"item": "WidgetB"} | {"item": "WidgetB", "lines": [2], "requested": 2.0, "in_stock": 10, "ok": true} |
| validator | check_price | {"line": 1} | {"line": 1, "item": "WidgetA", "invoiced": 250.0, "catalog": 250.0, "variance_pct": 0.0, "within_tolerance": true} |
| validator | check_price | {"line": 2} | {"line": 2, "item": "WidgetB", "invoiced": 500.0, "catalog": 500.0, "variance_pct": 0.0, "within_tolerance": true} |
| risk | get_vendor | {"name": "Widgets Inc."} | {"known": true, "name": "Widgets Inc.", "aliases": [], "first_seen": "2023-03-01", "earlier_invoices": [{"number": "INV-1001", "total": 5000.0, "status": "PAID" |

## Validator notes

```json
{
  "checks_run": [
    "resolve_item(1)",
    "resolve_item(2)",
    "resolve_item(3)",
    "check_stock(WidgetA)",
    "check_stock(WidgetB)",
    "check_price(1)",
    "check_price(2)",
    "check_totals",
    "check_duplicate",
    "get_vendor(Widgets Inc.)"
  ],
  "concerns": [
    "Line 3 (WidgetC) did not match any catalog item, so price and stock were not checked for it. Suggestions WidgetA and WidgetB are not matches."
  ],
  "summary": "Lines 1–2 match WidgetA and WidgetB at catalog price with sufficient stock; totals, vendor, and duplicate checks are clean. WidgetC is not in the catalog."
}
```

## Risk memo

```json
{
  "level": "low",
  "signals": [],
  "summary": "Widgets Inc. is a known vendor with a prior paid invoice, and this document shows ordinary Net 30 terms with no pressure, payment-redirect, reviewer instruction, or conflicting identity. Nothing here beyond the automated unknown-item finding suggests deception."
}
```

## VP draft 1

```json
{
  "action": "reject",
  "reasons": [
    {
      "text": "F1 is a reject-severity unknown-item finding: WidgetC is not in the inventory catalog, and the suggested names WidgetA and WidgetB are not matches. Price and stock were never checked for that line ($1,050). A reject finding blocks payment regardless of other factors.",
      "finding_ids": [
        "F1"
      ]
    }
  ],
  "addressed_findings": [
    "F1"
  ],
  "summary": "Reject INV-1016 from Widgets Inc. for $3,233. Automated check F1 (severity reject) flags WidgetC as not in the catalog, so the payment gate blocks this invoice."
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
  ]
}
```

## Resolution

```json
{
  "disposition": "return_to_vendor",
  "reasoning": "INV-1016 is rejected under F1 because line item WidgetC is not in the inventory catalog. Unknown items can be corrected and resubmitted, so policy requires return_to_vendor rather than void. The vendor must identify the intended catalog item and resubmit a corrected invoice before payment can proceed.",
  "vendor_reply": "Hello Widgets Inc. billing team, we cannot process invoice INV-1016 ($3,233.00) as submitted. Line item WidgetC (quantity 3, unit price $350.00, amount $1,050.00) is not in our catalog. Did you mean WidgetA or WidgetB? Please resubmit a corrected invoice that replaces WidgetC with the correct catalog item, with matching quantity, unit price, line amount, subtotal, tax, and total."
}
```
