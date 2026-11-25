# invoice_3003.csv: PAID

Paid 3,250.00 to Precision Parts Ltd.: Approve INV-3003 for $3,250 to Precision Parts Ltd. Known vendor, clean arithmetic, no findings, and a low-risk memo; the missing currency label does not block payment.

Run `20261125-033955-invoice_3003-9aef` · seconds 44.7 · llm_calls 8 · tool_calls 11 · tiers ['live'] · tokens 20866 · cost_usd 0.0145

## Extracted invoice

| field | value |
|---|---|
| invoice_number | INV-3003 |
| vendor | Precision Parts Ltd. |
| invoice_date | 2026-02-06 |
| due_date | 2026-03-08 |
| due_date_as_written | 2026-03-08 |
| currency | None |
| subtotal | 3250.0 |
| tax | 0.0 |
| shipping | None |
| total | 3250.0 |
| payment_terms | None |
| notes | None |
| revision | None |

| # | description | qty | unit price | amount | note |
|---|---|---|---|---|---|
| 1 | WidgetB | 5.0 | 500.0 | 2500.0 |  |
| 2 | GadgetX | 1.0 | 750.0 | 750.0 |  |

## Tool calls

| by | tool | args | result |
|---|---|---|---|
| validator | resolve_item | {"line": 1} | {"line": 1, "description": "WidgetB", "item": "WidgetB", "match": "exact"} |
| validator | resolve_item | {"line": 2} | {"line": 2, "description": "GadgetX", "item": "GadgetX", "match": "exact"} |
| validator | check_totals | {} | {"lines_sum": 3250.0, "expected_total": 3250.0, "stated_total": 3250.0, "problems": [], "ok": true} |
| validator | check_duplicate | {} | {"result": "no_match"} |
| validator | get_vendor | {"name": "Precision Parts Ltd."} | {"known": true, "name": "Precision Parts Ltd.", "aliases": [], "first_seen": "2024-01-08", "earlier_invoices": []} |
| validator | check_stock | {"item": "WidgetB"} | {"item": "WidgetB", "lines": [1], "requested": 5.0, "in_stock": 10, "ok": true} |
| validator | check_stock | {"item": "GadgetX"} | {"item": "GadgetX", "lines": [2], "requested": 1.0, "in_stock": 5, "ok": true} |
| validator | check_price | {"line": 1} | {"line": 1, "item": "WidgetB", "invoiced": 500.0, "catalog": 500.0, "variance_pct": 0.0, "within_tolerance": true} |
| validator | check_price | {"line": 2} | {"line": 2, "item": "GadgetX", "invoiced": 750.0, "catalog": 750.0, "variance_pct": 0.0, "within_tolerance": true} |
| risk | get_vendor | {"name": "Precision Parts Ltd."} | {"known": true, "name": "Precision Parts Ltd.", "aliases": [], "first_seen": "2024-01-08", "earlier_invoices": []} |
| approver | get_vendor | {"name": "Precision Parts Ltd."} | {"known": true, "name": "Precision Parts Ltd.", "aliases": [], "first_seen": "2024-01-08", "earlier_invoices": []} |

## Validator notes

```json
{
  "checks_run": [
    "resolve_item(1)",
    "resolve_item(2)",
    "check_stock(WidgetB)",
    "check_stock(GadgetX)",
    "check_price(1)",
    "check_price(2)",
    "check_totals",
    "check_duplicate",
    "get_vendor(Precision Parts Ltd.)"
  ],
  "concerns": [
    "Currency is missing on the invoice, so the amount is not labeled even though the arithmetic checks out.",
    "Vendor has been on the master since 2024-01-08 but the ledger lists no earlier invoices."
  ],
  "summary": "INV-3003 from Precision Parts Ltd. was checked against the catalog, stock, prices, totals, duplicate ledger, and vendor master. Both lines matched exactly, quantities are in stock, prices and totals agree, and no duplicate was found."
}
```

## Risk memo

```json
{
  "level": "low",
  "signals": [],
  "summary": "Precision Parts Ltd. is a known vendor, and the invoice is ordinary line-item billing with no pressure language, payment redirection, conflicting identity, or instructions to the reviewer. Nothing beyond the automated checks warrants holding payment."
}
```

## VP draft 1

```json
{
  "action": "approve",
  "reasons": [
    {
      "text": "Precision Parts Ltd. is on the vendor master (first seen 2024-01-08); lookup confirms a known vendor with no aliases. There are no automated findings, and the low-risk memo cites ordinary line-item billing with no pressure language, payment redirection, or conflicting identity.",
      "finding_ids": []
    },
    {
      "text": "Line amounts add up (5 × 500 + 1 × 750 = 3,250) and the total is under $10,000. Currency is unlabeled, and the ledger has no earlier invoices, but neither issue shows a document defect that makes the bill unsound.",
      "finding_ids": []
    }
  ],
  "addressed_findings": [],
  "summary": "Approve INV-3003 for $3,250 to Precision Parts Ltd. Known vendor, clean arithmetic, no findings, and a low-risk memo; the missing currency label does not block payment."
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
  "idempotency_key": "558d8c41a5a933a5ae21363d",
  "amount": 3250.0,
  "attempts": 1,
  "detail": ""
}
```
