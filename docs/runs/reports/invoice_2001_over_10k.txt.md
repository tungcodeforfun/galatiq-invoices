# invoice_2001_over_10k.txt: PAID

Paid 12,000.00 to Summit Manufacturing Co.: Approve INV-2001 for $12,000. Known vendor, low-risk memo, line math and Net 30 terms check out, and no findings block payment.

Run `20261125-015958-invoice_2001_over_10k-aaaf` · seconds 80.1 · llm_calls 9 · tool_calls 14 · tiers ['live'] · tokens 23727 · cost_usd 0.019

## Extracted invoice

| field | value |
|---|---|
| invoice_number | INV-2001 |
| vendor | Summit Manufacturing Co. |
| invoice_date | 2026-02-02 |
| due_date | 2026-03-04 |
| due_date_as_written | 2026-03-04 |
| currency | USD |
| subtotal | 11500.0 |
| tax | None |
| shipping | 500.0 |
| total | 12000.0 |
| payment_terms | Net 30 |
| notes | None |
| revision | None |

| # | description | qty | unit price | amount | note |
|---|---|---|---|---|---|
| 1 | WidgetA | 14.0 | 250.0 | 3500.0 |  |
| 2 | WidgetB | 10.0 | 500.0 | 5000.0 |  |
| 3 | GadgetX | 4.0 | 750.0 | 3000.0 |  |

## Tool calls

| by | tool | args | result |
|---|---|---|---|
| validator | resolve_item | {"line": 1} | {"line": 1, "description": "WidgetA", "item": "WidgetA", "match": "exact"} |
| validator | resolve_item | {"line": 2} | {"line": 2, "description": "WidgetB", "item": "WidgetB", "match": "exact"} |
| validator | resolve_item | {"line": 3} | {"line": 3, "description": "GadgetX", "item": "GadgetX", "match": "exact"} |
| validator | check_totals | {} | {"lines_sum": 11500.0, "expected_total": 12000.0, "stated_total": 12000.0, "problems": [], "ok": true} |
| validator | check_duplicate | {} | {"result": "no_match"} |
| validator | get_vendor | {"name": "Summit Manufacturing Co."} | {"known": true, "name": "Summit Manufacturing Co.", "aliases": [], "first_seen": "2023-04-22", "earlier_invoices": [{"number": "INV-1011", "total": 3000.0, "sta |
| validator | check_stock | {"item": "WidgetA"} | {"item": "WidgetA", "lines": [1], "requested": 14.0, "in_stock": 15, "ok": true} |
| validator | check_stock | {"item": "WidgetB"} | {"item": "WidgetB", "lines": [2], "requested": 10.0, "in_stock": 10, "ok": true} |
| validator | check_stock | {"item": "GadgetX"} | {"item": "GadgetX", "lines": [3], "requested": 4.0, "in_stock": 5, "ok": true} |
| validator | check_price | {"line": 1} | {"line": 1, "item": "WidgetA", "invoiced": 250.0, "catalog": 250.0, "variance_pct": 0.0, "within_tolerance": true} |
| validator | check_price | {"line": 2} | {"line": 2, "item": "WidgetB", "invoiced": 500.0, "catalog": 500.0, "variance_pct": 0.0, "within_tolerance": true} |
| validator | check_price | {"line": 3} | {"line": 3, "item": "GadgetX", "invoiced": 750.0, "catalog": 750.0, "variance_pct": 0.0, "within_tolerance": true} |
| risk | get_vendor | {"name": "Summit Manufacturing Co."} | {"known": true, "name": "Summit Manufacturing Co.", "aliases": [], "first_seen": "2023-04-22", "earlier_invoices": [{"number": "INV-1011", "total": 3000.0, "sta |
| approver | get_vendor | {"name": "Summit Manufacturing Co."} | {"known": true, "name": "Summit Manufacturing Co.", "aliases": [], "first_seen": "2023-04-22", "earlier_invoices": [{"number": "INV-1011", "total": 3000.0, "sta |

## Validator notes

```json
{
  "checks_run": [
    "resolve_item(line 1)",
    "resolve_item(line 2)",
    "resolve_item(line 3)",
    "check_stock(WidgetA)",
    "check_stock(WidgetB)",
    "check_stock(GadgetX)",
    "check_price(line 1)",
    "check_price(line 2)",
    "check_price(line 3)",
    "check_totals",
    "check_duplicate",
    "get_vendor(Summit Manufacturing Co.)"
  ],
  "concerns": [
    "Vendor history lists INV-1011 twice with conflicting outcomes (PAID, and REJECTED with disposition void). That is not this invoice, and check_duplicate found no match for INV-2001, but the ledger row looks inconsistent.",
    "WidgetB quantity equals on-hand stock exactly (10 of 10). check_stock still returned ok, so fulfilling this invoice would leave zero of that item."
  ],
  "summary": "INV-2001 from Summit Manufacturing Co. matched WidgetA, WidgetB, and GadgetX exactly; prices, stock, totals, and duplicate checks all passed with no tool-flagged problems. The only items for the approver are a contradictory prior INV-1011 in the vendor history and WidgetB consuming the entire on-hand quantity."
}
```

## Risk memo

```json
{
  "level": "low",
  "signals": [],
  "summary": "The invoice is a routine Net 30 bill from a known vendor, Summit Manufacturing Co., with no wording that suggests pressure, payment diversion, or identity conflict. Nothing in the document itself goes beyond the automated checks."
}
```

## VP draft 1

```json
{
  "action": "approve",
  "reasons": [
    {
      "text": "Risk memo is low: a routine Net 30 bill from Summit Manufacturing Co., on file since 2023-04-22, with no pressure, payment-diversion, or identity-conflict wording. Earlier INV-1011 was paid; the voided duplicate of that number does not affect this bill. No automated findings were raised.",
      "finding_ids": []
    },
    {
      "text": "Invoice is $12,000, so over the $10,000 scrutiny line. Line math holds (14×250=3,500; 10×500=5,000; 4×750=3,000; subtotal 11,500 plus shipping 500 = total 12,000). Due date 2026-03-04 matches Net 30 from 2026-02-02. The document itself shows no problem a check missed.",
      "finding_ids": []
    }
  ],
  "addressed_findings": [],
  "summary": "Approve INV-2001 for $12,000. Known vendor, low-risk memo, line math and Net 30 terms check out, and no findings block payment."
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
  "approved": true,
  "blocked_by": [],
  "overridden": false
}
```

## Payment

```json
{
  "status": "success",
  "idempotency_key": "506a1b892f861039eb641091",
  "amount": 12000.0,
  "attempts": 1,
  "detail": ""
}
```
