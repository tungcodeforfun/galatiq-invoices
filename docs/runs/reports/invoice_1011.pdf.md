# invoice_1011.pdf: PAID

Paid 3,000.00 to Summit Manufacturing Co.: Approve INV-1011 for $3,000. The known vendor's bill is internally consistent, has no findings, and the risk memo is low.

Run `20261125-034623-invoice_1011-c272` · seconds 33.0 · llm_calls 6 · tool_calls 9 · tiers ['live'] · tokens 15818 · cost_usd 0.0111

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

## Validator notes

```json
{
  "checks_run": [
    "resolve_item(line=1)",
    "resolve_item(line=2)",
    "check_stock(WidgetA)",
    "check_stock(WidgetB)",
    "check_price(line=1)",
    "check_price(line=2)",
    "check_totals",
    "check_duplicate",
    "get_vendor(Summit Manufacturing Co.)"
  ],
  "concerns": [
    "Subtotal, tax, and shipping are blank; the stated total equals the sum of the two line amounts only, which check_totals accepted.",
    "Vendor is known (first seen 2023-04-22) but the ledger lists no earlier invoices."
  ],
  "summary": "INV-1011 from Summit Manufacturing Co. was checked against the catalog, stock, prices, totals, the processed-invoice ledger, and the vendor master. Both lines matched WidgetA and WidgetB exactly; stock, prices, totals, and duplicate checks all came back clean."
}
```

## Risk memo

```json
{
  "level": "low",
  "signals": [],
  "summary": "The invoice is a standard two-line bill from Summit Manufacturing Co. with no pressure language, payment-redirect instructions, reviewer directives, or conflicting vendor identity. Nothing beyond the automated findings suggests deception or manipulation."
}
```

## VP draft 1

```json
{
  "action": "approve",
  "reasons": [
    {
      "text": "No automated findings were raised, and the $3,000 total matches the two line amounts (WidgetA $1,500 and WidgetB $1,500). Blank subtotal, tax, and shipping were accepted by the totals check and do not change the amount due.",
      "finding_ids": []
    },
    {
      "text": "Summit Manufacturing Co. is a known vendor (first seen 2023-04-22). The risk memo is low, with no pressure language, payment-redirect instructions, or conflicting identity, so the absence of earlier invoices in the ledger is not a reason to withhold payment.",
      "finding_ids": []
    }
  ],
  "addressed_findings": [],
  "summary": "Approve INV-1011 for $3,000. The known vendor's bill is internally consistent, has no findings, and the risk memo is low."
}
```

## Policy gate

```json
{
  "approved": true,
  "blocked_by": []
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
