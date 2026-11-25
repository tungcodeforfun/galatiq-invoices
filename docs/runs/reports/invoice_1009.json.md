# invoice_1009.json: REJECTED (void)

INV-1009 is voided under the data-integrity rule in F1: the vendor name is missing, line 1 quantity is -5.0, and the stated total is -250.0, so the document is corrupt and must not come back. F3 confirms it does not reconcile, with computed line amounts of -250.00 against a stated subtotal of 1,000.00. F2 (no due date) is a warning only and does not change the void.

Run `20261125-034344-invoice_1009-1880` · seconds 87.1 · llm_calls 8 · tool_calls 9 · tiers ['live'] · tokens 21464 · cost_usd 0.023

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
    "resolve_item(1)",
    "resolve_item(2)",
    "check_stock(WidgetA)",
    "check_stock(WidgetB)",
    "check_price(1)",
    "check_price(2)",
    "check_totals()",
    "check_duplicate()",
    "get_vendor(\"\")"
  ],
  "concerns": [
    "Line 1 quantity is negative (−5 WidgetA). check_stock returned ok because −5 does not exceed the 15 on hand, so a credit-style or erroneous quantity was not flagged.",
    "The stated total is negative while the stated subtotal is positive, and line amounts, shipping, due date, and payment terms are all blank. Together with no vendor, this reads like an incomplete credit rather than a normal payable."
  ],
  "summary": "Both lines matched the catalog exactly; unit prices are in tolerance and there is no ledger duplicate. Totals failed because the lines sum to −250.00 while the subtotal says 1,000.00, and the invoice names no vendor."
}
```

## Risk memo

```json
{
  "level": "low",
  "signals": [],
  "summary": "Nothing in the document shows pressure, payment redirection, instruction injection, or a conflicting vendor identity. The missing vendor, negative quantity, and total mismatch are already covered by the automated checks and are not separate fraud signals."
}
```

## VP draft 1

```json
{
  "action": "reject",
  "reasons": [
    {
      "text": "Vendor name is missing, line 1 quantity is −5 WidgetA, and the stated total is −250.00, so this is not a valid payable.",
      "finding_ids": [
        "F1"
      ]
    },
    {
      "text": "Computed line amounts are −250.00 (−5 × 250 + 2 × 500) while the stated subtotal is 1,000.00, so the invoice does not reconcile.",
      "finding_ids": [
        "F3"
      ]
    },
    {
      "text": "No due date is a warning only and would not block a sound invoice; it only confirms the document is incomplete.",
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
  "summary": "Reject INV-1009. Reject-severity data-integrity and total-mismatch findings block payment: no vendor, a negative quantity and total, and a subtotal that does not match the lines. The low-risk memo adds no separate fraud signal and does not override those blocks."
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
  "reasoning": "INV-1009 is voided under the data-integrity rule in F1: the vendor name is missing, line 1 quantity is -5.0, and the stated total is -250.0, so the document is corrupt and must not come back. F3 confirms it does not reconcile, with computed line amounts of -250.00 against a stated subtotal of 1,000.00. F2 (no due date) is a warning only and does not change the void.",
  "vendor_reply": null
}
```
