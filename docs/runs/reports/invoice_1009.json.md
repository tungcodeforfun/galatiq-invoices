# invoice_1009.json: REJECTED (void)

INV-1009 is voided because F1 is a data-integrity reject: the vendor name is missing, line 1 quantity is -5.0, and the total is -250.0, so there is no valid payee or payable. F3 is also a reject: the lines compute to -250.00 while the subtotal is stated as 1,000.00 and the amounts do not reconcile. F2 only warns that no due date is present and does not change the required void.

Run `20261125-014614-invoice_1009-0aa4` · seconds 101.1 · llm_calls 8 · tool_calls 9 · tiers ['live'] · tokens 21120 · cost_usd 0.026

## Extracted invoice

| field | value |
|---|---|
| invoice_number | INV-1009 |
| vendor | None |
| invoice_date | 2026-01-15 |
| due_date | None |
| due_date_as_written | None |
| currency | USD |
| subtotal | 1000.0 |
| tax | 0.0 |
| shipping | None |
| total | -250.0 |
| payment_terms | None |
| notes | None |
| revision | None |

| # | description | qty | unit price | amount | note |
|---|---|---|---|---|---|
| 1 | WidgetA | -5.0 | 250.0 | None |  |
| 2 | WidgetB | 2.0 | 500.0 | None |  |

## Findings

| id | code | severity | message | source |
|---|---|---|---|---|
| F1 | DATA_INTEGRITY | reject | vendor name is missing; line 1 quantity is -5.0; total is -250.0 | rules |
| F2 | DATE_ODDITY | warn | No due date | rules |
| F3 | TOTAL_MISMATCH | reject | lines add up to -250.00, subtotal says 1,000.00 | check_totals |

## Tool calls

| by | tool | args | result |
|---|---|---|---|
| validator | resolve_item | {"line": 1} | {"line": 1, "description": "WidgetA", "item": "WidgetA", "match": "exact"} |
| validator | resolve_item | {"line": 2} | {"line": 2, "description": "WidgetB", "item": "WidgetB", "match": "exact"} |
| validator | check_totals | {} | {"lines_sum": -250.0, "expected_total": -250.0, "stated_total": -250.0, "problems": ["lines add up to -250.00, subtotal says 1,000.00"], "ok": false} |
| validator | check_duplicate | {} | {"result": "no_match"} |
| validator | get_vendor | {"name": ""} | {"known": false, "name": "", "note": "the invoice names no vendor"} |
| validator | check_stock | {"item": "WidgetA"} | {"item": "WidgetA", "lines": [1], "requested": -5.0, "in_stock": 15, "ok": true} |
| validator | check_stock | {"item": "WidgetB"} | {"item": "WidgetB", "lines": [2], "requested": 2.0, "in_stock": 10, "ok": true} |
| validator | check_price | {"line": 1} | {"line": 1, "item": "WidgetA", "invoiced": 250.0, "catalog": 250.0, "variance_pct": 0.0, "within_tolerance": true} |
| validator | check_price | {"line": 2} | {"line": 2, "item": "WidgetB", "invoiced": 500.0, "catalog": 500.0, "variance_pct": 0.0, "within_tolerance": true} |

## Validator notes

```json
{
  "checks_run": [
    "resolve_item(line 1)",
    "resolve_item(line 2)",
    "check_stock(WidgetA)",
    "check_stock(WidgetB)",
    "check_price(line 1)",
    "check_price(line 2)",
    "check_totals",
    "check_duplicate",
    "get_vendor(\"\")"
  ],
  "concerns": [
    "Line 1 quantity is negative (−5 WidgetA). check_stock returned ok only because −5 is below on-hand stock, so the sign itself was not treated as a problem. A negative quantity on a payable invoice may be a return, a credit, or an extraction error.",
    "Stated total is negative (−250) and matches the recomputed line sum, so this may be a credit rather than an amount to pay. check_totals only flagged that the stated subtotal (1,000) does not match that line sum.",
    "No vendor name is on the invoice, so there is no payee to match even though prices matched the catalog and no duplicate was found. Due date, payment terms, shipping, and line amounts are also blank."
  ],
  "summary": "Both lines matched the catalog (WidgetA, WidgetB); unit prices match and stock checks passed, including a negative WidgetA quantity that was not flagged. Totals do not: lines and the stated total are −250 while the subtotal says 1,000, the vendor field is empty, and the invoice is not a known duplicate."
}
```

## Risk memo

```json
{
  "level": "low",
  "signals": [],
  "summary": "The invoice has no pressure language, payment-redirect instructions, reviewer-directed text, or conflicting vendor identity beyond the missing name already flagged. Nothing in the document itself adds a fraud signal past the automated data-integrity and total findings."
}
```

## VP draft 1

```json
{
  "action": "reject",
  "reasons": [
    {
      "text": "F1 is a reject finding: vendor name is missing, WidgetA quantity is -5, and the invoice total is -250. There is no payee and this is not a valid payable.",
      "finding_ids": [
        "F1"
      ]
    },
    {
      "text": "F3 is a reject finding: lines compute to -250.00 (-5 × 250 + 2 × 500) but the subtotal is stated as 1,000.00, so the amount does not reconcile and cannot be paid.",
      "finding_ids": [
        "F3"
      ]
    },
    {
      "text": "F2 warns there is no due date. That alone would not block payment, but it does not cure the reject findings. The risk memo is low and adds no offsetting comfort.",
      "finding_ids": [
        "F2"
      ]
    }
  ],
  "addressed_findings": [
    "F1",
    "F2",
    "F3"
  ],
  "summary": "Reject INV-1009. Missing vendor, a negative quantity and total, and a subtotal that does not match the lines are hard stops; the missing due date and low risk memo do not make it payable."
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
  "reasoning": "INV-1009 is voided because F1 is a data-integrity reject: the vendor name is missing, line 1 quantity is -5.0, and the total is -250.0, so there is no valid payee or payable. F3 is also a reject: the lines compute to -250.00 while the subtotal is stated as 1,000.00 and the amounts do not reconcile. F2 only warns that no due date is present and does not change the required void.",
  "vendor_reply": null
}
```
