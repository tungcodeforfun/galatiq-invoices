# invoice_2001_over_10k.txt: PAID

Paid 12,000.00 to Summit Manufacturing Co.: Approve INV-2001 for $12,000. Summit Manufacturing is on file, the low-risk memo and invoice math are clean, and the older INV-1011 status conflict is not a duplicate of this bill.

Run `20261125-035755-invoice_2001_over_10k-8754` · seconds 75.3 · llm_calls 9 · tool_calls 14 · tiers ['live'] · tokens 24103 · cost_usd 0.0219

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
    "resolve_item(line=1)",
    "resolve_item(line=2)",
    "resolve_item(line=3)",
    "check_stock(WidgetA)",
    "check_stock(WidgetB)",
    "check_stock(GadgetX)",
    "check_price(line=1)",
    "check_price(line=2)",
    "check_price(line=3)",
    "check_totals",
    "check_duplicate",
    "get_vendor(Summit Manufacturing Co.)"
  ],
  "concerns": [
    "Vendor history lists INV-1011 twice with the same total: once PAID and once REJECTED/void. That conflict is not on this invoice (check_duplicate found no match) but is worth a look before approving further Summit invoices."
  ],
  "summary": "INV-2001 from Summit Manufacturing Co. matched catalog items WidgetA, WidgetB, and GadgetX. Stock, unit prices, totals, and duplicate checks all passed with no tool-flagged problems."
}
```

## Risk memo

```json
{
  "level": "low",
  "signals": [],
  "summary": "The invoice is from a known vendor and contains only ordinary commercial wording, including Net 30 terms and a PO reference. Nothing on the document indicates deception or manipulation beyond the automated checks."
}
```

## VP draft 1

```json
{
  "action": "approve",
  "reasons": [
    {
      "text": "Risk memo is low: known vendor, ordinary commercial wording including Net 30, and no deception or manipulation signals. No automated findings were raised, so nothing blocks payment.",
      "finding_ids": []
    },
    {
      "text": "Summit Manufacturing Co. is on file since 2023-04-22. Invoice math holds: 14×250 + 10×500 + 4×750 = 11,500 subtotal, plus 500 shipping = 12,000 total. Due date 2026-03-04 matches Net 30 from 2026-02-02.",
      "finding_ids": []
    },
    {
      "text": "Vendor history shows INV-1011 both PAID and REJECTED/void at $3,000, but that conflict is not on this invoice and the duplicate check found no match. It does not outweigh a clean low-risk bill from a vendor on file.",
      "finding_ids": []
    }
  ],
  "addressed_findings": [],
  "summary": "Approve INV-2001 for $12,000. Summit Manufacturing is on file, the low-risk memo and invoice math are clean, and the older INV-1011 status conflict is not a duplicate of this bill."
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
  "blocked_by": []
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
