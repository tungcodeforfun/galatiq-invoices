# invoice_1011.pdf: PAID

Paid 3,000.00 to Summit Manufacturing Co.: Approve INV-1011 for $3,000 to Summit Manufacturing Co. Known vendor, line items match the total, no findings, and the risk memo is low.

Run `20261125-014856-invoice_1011-6fb2` · seconds 28.9 · llm_calls 8 · tool_calls 11 · tiers ['live'] · tokens 20462 · cost_usd 0.012

## Extracted invoice

| field | value |
|---|---|
| invoice_number | INV-1011 |
| vendor | Summit Manufacturing Co. |
| invoice_date | 2026-01-20 |
| due_date | 2026-02-20 |
| due_date_as_written | 2026-02-20 |
| currency | USD |
| subtotal | None |
| tax | None |
| shipping | None |
| total | 3000.0 |
| payment_terms | None |
| notes | None |
| revision | None |

| # | description | qty | unit price | amount | note |
|---|---|---|---|---|---|
| 1 | WidgetA | 6.0 | 250.0 | 1500.0 |  |
| 2 | WidgetB | 3.0 | 500.0 | 1500.0 |  |

## Tool calls

| by | tool | args | result |
|---|---|---|---|
| validator | resolve_item | {"line": 1} | {"line": 1, "description": "WidgetA", "item": "WidgetA", "match": "exact"} |
| validator | resolve_item | {"line": 2} | {"line": 2, "description": "WidgetB", "item": "WidgetB", "match": "exact"} |
| validator | check_totals | {} | {"lines_sum": 3000.0, "expected_total": 3000.0, "stated_total": 3000.0, "problems": [], "ok": true} |
| validator | check_duplicate | {} | {"result": "no_match"} |
| validator | get_vendor | {"name": "Summit Manufacturing Co."} | {"known": true, "name": "Summit Manufacturing Co.", "aliases": [], "first_seen": "2023-04-22", "earlier_invoices": []} |
| validator | check_stock | {"item": "WidgetA"} | {"item": "WidgetA", "lines": [1], "requested": 6.0, "in_stock": 15, "ok": true} |
| validator | check_stock | {"item": "WidgetB"} | {"item": "WidgetB", "lines": [2], "requested": 3.0, "in_stock": 10, "ok": true} |
| validator | check_price | {"line": 1} | {"line": 1, "item": "WidgetA", "invoiced": 250.0, "catalog": 250.0, "variance_pct": 0.0, "within_tolerance": true} |
| validator | check_price | {"line": 2} | {"line": 2, "item": "WidgetB", "invoiced": 500.0, "catalog": 500.0, "variance_pct": 0.0, "within_tolerance": true} |
| risk | get_vendor | {"name": "Summit Manufacturing Co."} | {"known": true, "name": "Summit Manufacturing Co.", "aliases": [], "first_seen": "2023-04-22", "earlier_invoices": []} |
| approver | get_vendor | {"name": "Summit Manufacturing Co."} | {"known": true, "name": "Summit Manufacturing Co.", "aliases": [], "first_seen": "2023-04-22", "earlier_invoices": []} |

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
    "get_vendor(Summit Manufacturing Co.)"
  ],
  "concerns": [
    "Vendor is known since 2023-04-22 but the ledger lists no earlier invoices, so there is no payment history to compare."
  ],
  "summary": "INV-1011 from Summit Manufacturing Co. matched WidgetA and WidgetB exactly; stock, prices, totals, and duplicate checks all came back clean."
}
```

## Risk memo

```json
{
  "level": "low",
  "signals": [],
  "summary": "Summit Manufacturing Co. is a known vendor, and this invoice has no unusual wording, payment instructions, or conflicting identity. Nothing here goes beyond the automated checks."
}
```

## VP draft 1

```json
{
  "action": "approve",
  "reasons": [
    {
      "text": "Vendor Summit Manufacturing Co. is on file (known since 2023-04-22). Invoice total is $3,000, under the $10,000 extra-scrutiny threshold, and line items sum exactly to the total (6 x $250 + 3 x $500).",
      "finding_ids": []
    },
    {
      "text": "No automated findings were raised. The risk memo is low, with no unusual wording, payment instructions, or identity conflict, so nothing outweighs paying a known vendor whose checks pass.",
      "finding_ids": []
    }
  ],
  "addressed_findings": [],
  "summary": "Approve INV-1011 for $3,000 to Summit Manufacturing Co. Known vendor, line items match the total, no findings, and the risk memo is low."
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
  "idempotency_key": "59d328f8ed71e4408988b916",
  "amount": 3000.0,
  "attempts": 1,
  "detail": ""
}
```
