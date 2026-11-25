# invoice_3007.json: REJECTED (return_to_vendor)

F1 is a reject-severity stock finding: WidgetB is billed for 11 units across two lines (6 and 5) against 10 on hand, so the quantity is over what we can accept and payment is blocked. Policy requires return_to_vendor for quantities over what we can accept, and the invoice is not a duplicate, corrupt, or fraudulent document that must be voided. The vendor can correct the quantity and resubmit.

Run `20261125-034312-invoice_3007-2b8d` · seconds 58.7 · llm_calls 9 · tool_calls 9 · tiers ['live'] · tokens 23163 · cost_usd 0.019

## Extracted invoice

| field | value |
|---|---|
| invoice_number | INV-3007 |
| vendor | Consolidated Materials Group |
| invoice_date | 2026-02-12 |
| due_date | 2026-03-14 |
| due_date_as_written | 2026-03-14 |
| currency | USD |
| subtotal | 5500.0 |
| tax | None |
| shipping | None |
| total | 5500.0 |
| payment_terms | Net 30 |
| notes | None |
| revision | None |

| # | description | qty | unit price | amount | note |
|---|---|---|---|---|---|
| 1 | WidgetB | 6.0 | 500.0 | 3000.0 | first delivery |
| 2 | WidgetB | 5.0 | 500.0 | 2500.0 | second delivery |

## Findings

| id | code | severity | message | source |
|---|---|---|---|---|
| F1 | STOCK_EXCEEDED | reject | WidgetB: 11 requested across 2 line(s), 10 in stock | check_stock |

## Tool calls

| by | tool | args | result |
|---|---|---|---|
| validator | resolve_item | {"line": 1} | {"line": 1, "description": "WidgetB", "item": "WidgetB", "match": "exact"} |
| validator | resolve_item | {"line": 2} | {"line": 2, "description": "WidgetB", "item": "WidgetB", "match": "exact"} |
| validator | check_totals | {} | {"lines_sum": 5500.0, "expected_total": 5500.0, "stated_total": 5500.0, "problems": [], "ok": true} |
| validator | check_duplicate | {} | {"result": "no_match"} |
| validator | get_vendor | {"name": "Consolidated Materials Group"} | {"known": true, "name": "Consolidated Materials Group", "aliases": [], "first_seen": "2023-09-14", "earlier_invoices": []} |
| validator | check_stock | {"item": "WidgetB"} | {"item": "WidgetB", "lines": [1, 2], "requested": 11.0, "in_stock": 10, "ok": false} |
| validator | check_price | {"line": 1} | {"line": 1, "item": "WidgetB", "invoiced": 500.0, "catalog": 500.0, "variance_pct": 0.0, "within_tolerance": true} |
| validator | check_price | {"line": 2} | {"line": 2, "item": "WidgetB", "invoiced": 500.0, "catalog": 500.0, "variance_pct": 0.0, "within_tolerance": true} |
| risk | get_vendor | {"name": "Consolidated Materials Group"} | {"known": true, "name": "Consolidated Materials Group", "aliases": [], "first_seen": "2023-09-14", "earlier_invoices": []} |

## Validator notes

```json
{
  "checks_run": [
    "resolve_item(line 1)",
    "resolve_item(line 2)",
    "check_stock(WidgetB)",
    "check_price(line 1)",
    "check_price(line 2)",
    "check_totals",
    "check_duplicate",
    "get_vendor(Consolidated Materials Group)"
  ],
  "concerns": [
    "Both lines are the same catalog item (WidgetB), split as first and second delivery (6 and 5). Stock was checked once on the combined quantity: 11 requested versus 10 on hand, so the invoice is one unit over stock, not two separate stock failures.",
    "Tax and shipping are blank; totals still match the line amounts only. Vendor is known (first seen 2023-09-14) but has no earlier invoices on file."
  ],
  "summary": "Both WidgetB lines matched the catalog at the catalog price, totals reconcile, and this is not a duplicate. The only tool failure is stock: combined quantity 11 exceeds the 10 on hand."
}
```

## Risk memo

```json
{
  "level": "low",
  "signals": [],
  "summary": "No deception or manipulation signals appear on the invoice beyond the automated stock finding. Vendor identity matches the master and payment wording is ordinary Net 30."
}
```

## VP draft 1

```json
{
  "action": "reject",
  "reasons": [
    {
      "text": "F1 is a reject-severity stock finding: WidgetB quantity across both lines is 11 against 10 on hand. Combined stock was already checked once, so the invoice is one unit over available stock and the payment gate blocks it.",
      "finding_ids": [
        "F1"
      ]
    }
  ],
  "addressed_findings": [
    "F1"
  ],
  "summary": "Reject INV-3007. WidgetB is billed for 11 units and only 10 are in stock (F1, reject severity), so payment is blocked. The low risk memo and matching $5,500 total do not override that finding."
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
  "reasoning": "F1 is a reject-severity stock finding: WidgetB is billed for 11 units across two lines (6 and 5) against 10 on hand, so the quantity is over what we can accept and payment is blocked. Policy requires return_to_vendor for quantities over what we can accept, and the invoice is not a duplicate, corrupt, or fraudulent document that must be voided. The vendor can correct the quantity and resubmit.",
  "vendor_reply": "Hello Consolidated Materials Group billing team, Invoice INV-3007 cannot be processed as submitted. WidgetB appears on two lines for quantities of 6 and 5 (11 units total at $500 each; line amounts $3,000.00 and $2,500.00; invoice total $5,500.00), which is more than the quantity we can accept. Please resubmit a corrected invoice with a reduced WidgetB quantity we can accept, and with each line amount and the invoice total recalculated to match that quantity. Thank you."
}
```
