# invoice_3011.eml: REJECTED (void)

INV-3011 is voided under F1 because it matches already-paid INV-3001 for Widgets Inc., with the same line items and a $3,780.00 total. Paying it would settle the same invoice twice. Policy requires void for duplicates so the document cannot be resubmitted.

Run `20261125-034712-invoice_3011-8fa4` · seconds 63.0 · llm_calls 8 · tool_calls 9 · tiers ['live'] · tokens 20389 · cost_usd 0.0171

## Extracted invoice

| field | value |
|---|---|
| invoice_number | INV-3011 |
| vendor | Widgets Inc. |
| invoice_date | 2026-02-18 |
| due_date | 2026-03-20 |
| due_date_as_written | 2026-03-20 |
| currency | USD |
| subtotal | 3500.0 |
| tax | 280.0 |
| shipping | None |
| total | 3780.0 |
| payment_terms | Net 30 |
| notes | Hi Acme AP team,  Please find our invoice below for this month's order.  Best regards, Accounts Receivable Widgets Inc. |
| revision | None |

| # | description | qty | unit price | amount | note |
|---|---|---|---|---|---|
| 1 | WidgetA | 8.0 | 250.0 | None |  |
| 2 | WidgetB | 3.0 | 500.0 | None |  |

## Findings

| id | code | severity | message | source |
|---|---|---|---|---|
| F1 | DUPLICATE | reject | Same vendor, lines and total as INV-3001 (PAID) | check_duplicate |

## Tool calls

| by | tool | args | result |
|---|---|---|---|
| validator | resolve_item | {"line": 1} | {"line": 1, "description": "WidgetA", "item": "WidgetA", "match": "exact"} |
| validator | resolve_item | {"line": 2} | {"line": 2, "description": "WidgetB", "item": "WidgetB", "match": "exact"} |
| validator | check_totals | {} | {"lines_sum": 3500.0, "expected_total": 3780.0, "stated_total": 3780.0, "problems": [], "ok": true} |
| validator | check_duplicate | {} | {"result": "duplicate", "of": "INV-3001", "prior_status": "PAID"} |
| validator | get_vendor | {"name": "Widgets Inc."} | {"known": true, "name": "Widgets Inc.", "aliases": [], "first_seen": "2023-03-01", "earlier_invoices": [{"number": "INV-3001", "total": 3780.0, "status": "PAID" |
| validator | check_stock | {"item": "WidgetA"} | {"item": "WidgetA", "lines": [1], "requested": 8.0, "in_stock": 15, "ok": true} |
| validator | check_stock | {"item": "WidgetB"} | {"item": "WidgetB", "lines": [2], "requested": 3.0, "in_stock": 10, "ok": true} |
| validator | check_price | {"line": 1} | {"line": 1, "item": "WidgetA", "invoiced": 250.0, "catalog": 250.0, "variance_pct": 0.0, "within_tolerance": true} |
| validator | check_price | {"line": 2} | {"line": 2, "item": "WidgetB", "invoiced": 500.0, "catalog": 500.0, "variance_pct": 0.0, "within_tolerance": true} |

## Validator notes

```json
{
  "checks_run": [
    "resolve_item(1)",
    "resolve_item(2)",
    "check_stock(WidgetA)",
    "check_stock(WidgetB)",
    "check_price(1)",
    "check_price(2)",
    "check_totals",
    "check_duplicate",
    "get_vendor(Widgets Inc.)"
  ],
  "concerns": [
    "INV-3011 matches already-paid INV-3001 (same vendor and total of 3780.00). Do not pay again; treat as a resubmission of a settled invoice."
  ],
  "summary": "Both lines matched the catalog (WidgetA, WidgetB); stock and unit prices were within tolerance and stated totals reconciled. The invoice is a duplicate of paid INV-3001 for known vendor Widgets Inc."
}
```

## Risk memo

```json
{
  "level": "low",
  "signals": [],
  "summary": "The invoice itself shows no pressure language, payment redirect, instruction injection, or conflicting vendor identity. The duplicate finding is already covered by automated checks and is not restated here."
}
```

## VP draft 1

```json
{
  "action": "reject",
  "reasons": [
    {
      "text": "F1 is a reject-severity duplicate: INV-3011 has the same vendor, lines, and $3,780.00 total as already-paid INV-3001. Paying it would settle the same invoice twice. The low-risk memo does not override that block.",
      "finding_ids": [
        "F1"
      ]
    }
  ],
  "addressed_findings": [
    "F1"
  ],
  "summary": "Reject INV-3011. It is a resubmission of paid INV-3001 (Widgets Inc., $3,780.00); the duplicate check blocks payment."
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
  "disposition": "void",
  "reasoning": "INV-3011 is voided under F1 because it matches already-paid INV-3001 for Widgets Inc., with the same line items and a $3,780.00 total. Paying it would settle the same invoice twice. Policy requires void for duplicates so the document cannot be resubmitted.",
  "vendor_reply": null
}
```
