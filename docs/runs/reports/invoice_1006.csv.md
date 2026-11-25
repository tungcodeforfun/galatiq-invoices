# invoice_1006.csv: PAID

Paid 2,750.00 to Acme Industrial Supplies: Approve INV-1006 for $2,750. Acme Industrial Supplies is a known vendor, the total matches the line math, and the low-risk memo has no blocking findings.

Run `20261125-033801-invoice_1006-d0fc` · seconds 60.9 · llm_calls 8 · tool_calls 11 · tiers ['live'] · tokens 20996 · cost_usd 0.017

## Extracted invoice

| field | value |
|---|---|
| invoice_number | INV-1006 |
| vendor | Acme Industrial Supplies |
| invoice_date | 2026-01-25 |
| due_date | 2026-02-10 |
| due_date_as_written | 2026-02-10 |
| currency | None |
| subtotal | 2750.0 |
| tax | 0.0 |
| shipping | None |
| total | 2750.0 |
| payment_terms | Net 15 |
| notes | None |
| revision | None |

| # | description | qty | unit price | amount | note |
|---|---|---|---|---|---|
| 1 | WidgetA | 5.0 | 250.0 | None |  |
| 2 | WidgetB | 3.0 | 500.0 | None |  |

## Tool calls

| by | tool | args | result |
|---|---|---|---|
| validator | resolve_item | {"line": 1} | {"line": 1, "description": "WidgetA", "item": "WidgetA", "match": "exact"} |
| validator | resolve_item | {"line": 2} | {"line": 2, "description": "WidgetB", "item": "WidgetB", "match": "exact"} |
| validator | check_totals | {} | {"lines_sum": 2750.0, "expected_total": 2750.0, "stated_total": 2750.0, "problems": [], "ok": true} |
| validator | check_duplicate | {} | {"result": "no_match"} |
| validator | get_vendor | {"name": "Acme Industrial Supplies"} | {"known": true, "name": "Acme Industrial Supplies", "aliases": [], "first_seen": "2022-11-30", "earlier_invoices": []} |
| validator | check_stock | {"item": "WidgetA"} | {"item": "WidgetA", "lines": [1], "requested": 5.0, "in_stock": 15, "ok": true} |
| validator | check_stock | {"item": "WidgetB"} | {"item": "WidgetB", "lines": [2], "requested": 3.0, "in_stock": 10, "ok": true} |
| validator | check_price | {"line": 1} | {"line": 1, "item": "WidgetA", "invoiced": 250.0, "catalog": 250.0, "variance_pct": 0.0, "within_tolerance": true} |
| validator | check_price | {"line": 2} | {"line": 2, "item": "WidgetB", "invoiced": 500.0, "catalog": 500.0, "variance_pct": 0.0, "within_tolerance": true} |
| risk | get_vendor | {"name": "Acme Industrial Supplies"} | {"known": true, "name": "Acme Industrial Supplies", "aliases": [], "first_seen": "2022-11-30", "earlier_invoices": []} |
| approver | get_vendor | {"name": "Acme Industrial Supplies"} | {"known": true, "name": "Acme Industrial Supplies", "aliases": [], "first_seen": "2022-11-30", "earlier_invoices": []} |

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
    "get_vendor(Acme Industrial Supplies)"
  ],
  "concerns": [
    "Vendor is known (first seen 2022-11-30) but the ledger lists no earlier invoices.",
    "Currency, shipping, and both line amounts are null on the extraction; totals still matched the stated 2750 with no tool problem."
  ],
  "summary": "Checked both lines against the catalog, stock, and price, plus totals, duplicates, and the vendor master. No tool flagged a mismatch, stock issue, price variance, total error, or duplicate."
}
```

## Risk memo

```json
{
  "level": "low",
  "signals": [],
  "summary": "Acme Industrial Supplies is a known vendor and the invoice shows ordinary Net 15 terms with no payment-redirect, identity conflict, or reviewer instructions. Nothing in the document suggests deception beyond the automated checks."
}
```

## VP draft 1

```json
{
  "action": "approve",
  "reasons": [
    {
      "text": "Vendor Acme Industrial Supplies is on file (first seen 2022-11-30). There are no findings, and the risk memo is low: ordinary Net 15 terms, no payment redirect, identity conflict, or reviewer instructions.",
      "finding_ids": []
    },
    {
      "text": "Amount is $2,750, under the $10,000 extra-scrutiny threshold. Line math reconciles (5 x 250 = 1,250; 3 x 500 = 1,500; tax 0; total 2,750). Null extracted currency, shipping, and line amounts do not contradict the stated total.",
      "finding_ids": []
    }
  ],
  "addressed_findings": [],
  "summary": "Approve INV-1006 for $2,750. Acme Industrial Supplies is a known vendor, the total matches the line math, and the low-risk memo has no blocking findings."
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
  "idempotency_key": "4b4351aea897956af2af21c3",
  "amount": 2750.0,
  "attempts": 1,
  "detail": ""
}
```
