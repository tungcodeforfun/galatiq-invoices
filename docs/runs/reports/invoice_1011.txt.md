# invoice_1011.txt: REJECTED (void)

INV-1011 from Summit Manufacturing Co. is rejected under F1 because it matches the vendor, line items, and total of INV-1011, which is already PAID. Policy requires void for a duplicate so the invoice cannot be resubmitted or paid again.

Run `20261125-034657-invoice_1011-4d9d` · seconds 44.3 · llm_calls 9 · tool_calls 10 · tiers ['live'] · tokens 22401 · cost_usd 0.0144

## Extracted invoice

| field | value |
|---|---|
| invoice_number | INV-1011 |
| vendor | Summit Manufacturing Co. |
| invoice_date | 2026-01-20 |
| due_date | 2026-02-20 |
| due_date_as_written | 2026-02-20 |
| currency | USD |
| subtotal | 3000.0 |
| tax | 0.0 |
| shipping | None |
| total | 3000.0 |
| payment_terms | Net 30 |
| notes | None |
| revision | None |

| # | description | qty | unit price | amount | note |
|---|---|---|---|---|---|
| 1 | WidgetA | 6.0 | 250.0 | 1500.0 |  |
| 2 | WidgetB | 3.0 | 500.0 | 1500.0 |  |

## Findings

| id | code | severity | message | source |
|---|---|---|---|---|
| F1 | DUPLICATE | reject | Same vendor, lines and total as INV-1011 (PAID) | check_duplicate |

## Tool calls

| by | tool | args | result |
|---|---|---|---|
| validator | resolve_item | {"line": 1} | {"line": 1, "description": "WidgetA", "item": "WidgetA", "match": "exact"} |
| validator | resolve_item | {"line": 2} | {"line": 2, "description": "WidgetB", "item": "WidgetB", "match": "exact"} |
| validator | check_totals | {} | {"lines_sum": 3000.0, "expected_total": 3000.0, "stated_total": 3000.0, "problems": [], "ok": true} |
| validator | check_duplicate | {} | {"result": "duplicate", "of": "INV-1011", "prior_status": "PAID"} |
| validator | get_vendor | {"name": "Summit Manufacturing Co."} | {"known": true, "name": "Summit Manufacturing Co.", "aliases": [], "first_seen": "2023-04-22", "earlier_invoices": [{"number": "INV-1011", "total": 3000.0, "sta |
| validator | check_stock | {"item": "WidgetA"} | {"item": "WidgetA", "lines": [1], "requested": 6.0, "in_stock": 15, "ok": true} |
| validator | check_stock | {"item": "WidgetB"} | {"item": "WidgetB", "lines": [2], "requested": 3.0, "in_stock": 10, "ok": true} |
| validator | check_price | {"line": 1} | {"line": 1, "item": "WidgetA", "invoiced": 250.0, "catalog": 250.0, "variance_pct": 0.0, "within_tolerance": true} |
| validator | check_price | {"line": 2} | {"line": 2, "item": "WidgetB", "invoiced": 500.0, "catalog": 500.0, "variance_pct": 0.0, "within_tolerance": true} |
| risk | get_vendor | {"name": "Summit Manufacturing Co."} | {"known": true, "name": "Summit Manufacturing Co.", "aliases": [], "first_seen": "2023-04-22", "earlier_invoices": [{"number": "INV-1011", "total": 3000.0, "sta |

## Validator notes

```json
{
  "checks_run": [
    "resolve_item(line 1)",
    "resolve_item(line 2)",
    "check_totals",
    "check_duplicate",
    "get_vendor(Summit Manufacturing Co.)",
    "check_stock(WidgetA)",
    "check_stock(WidgetB)",
    "check_price(line 1)",
    "check_price(line 2)"
  ],
  "concerns": [],
  "summary": "Both lines matched the catalog exactly (WidgetA, WidgetB); stock, unit prices, and totals all checked out. check_duplicate and the vendor master both show INV-1011 already processed and PAID, so this looks like a resubmission of a paid invoice."
}
```

## Risk memo

```json
{
  "level": "low",
  "signals": [],
  "summary": "The invoice is ordinary Net 30 wording from a known vendor, with no pressure language, payment redirect, instruction injection, or conflicting vendor identity. Nothing here goes beyond the automated duplicate finding, which the VP already sees separately."
}
```

## VP draft 1

```json
{
  "action": "reject",
  "reasons": [
    {
      "text": "F1 is a reject-severity duplicate: same vendor, lines, and total as INV-1011, which is already PAID. The payment gate blocks this invoice regardless of any other weighing.",
      "finding_ids": [
        "F1"
      ]
    }
  ],
  "addressed_findings": [
    "F1"
  ],
  "summary": "Reject INV-1011 from Summit Manufacturing Co. for $3,000. It is a duplicate of an invoice already paid (F1), so it must not be paid again."
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
  "reasoning": "INV-1011 from Summit Manufacturing Co. is rejected under F1 because it matches the vendor, line items, and total of INV-1011, which is already PAID. Policy requires void for a duplicate so the invoice cannot be resubmitted or paid again.",
  "vendor_reply": null
}
```
