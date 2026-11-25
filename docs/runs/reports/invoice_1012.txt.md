# invoice_1012.txt: REJECTED (void)

F3 is a reject-severity duplicate: this document matches already-paid INV 1012 from QuickShip Distributers on vendor, lines, and total 9,975.00, so it must not be paid again or returned for resubmission. F1 (total just under the 10,000 approval line) and F2 (OCR normalizations of the invoice date and a line amount) are informational only and do not create a new payable or offset the duplicate. Disposition is void.

Run `20261125-034942-invoice_1012-25d0` · seconds 127.1 · llm_calls 10 · tool_calls 15 · tiers ['live', 'replay'] · tokens 27836 · cost_usd 0.0322

## Extracted invoice

| field | value |
|---|---|
| invoice_number | INV 1012 |
| vendor | QuickShip Distributers |
| invoice_date | 2026-01-26 |
| due_date | 2026-02-25 |
| due_date_as_written | 25-Feb-2026 |
| currency | USD |
| subtotal | 9500.0 |
| tax | 475.0 |
| shipping | None |
| total | 9975.0 |
| payment_terms | Net 30 |
| notes | Ref PO-20260115. Deliver to warehouse dock B. Contact Jim at ext 4421 with questions. |
| revision | None |

| # | description | qty | unit price | amount | note |
|---|---|---|---|---|---|
| 1 | Widget A | 12.0 | 250.0 | 3000.0 |  |
| 2 | WidgetB | 7.0 | 500.0 | 3500.0 |  |
| 3 | Gadget X | 4.0 | 750.0 | 3000.0 |  |

## Findings

| id | code | severity | message | source |
|---|---|---|---|---|
| F1 | NEAR_THRESHOLD | info | Total 9,975.00 sits just under the 10,000 approval line | rules |
| F2 | OCR_CORRECTED | info | invoice_date: '26-Jan-2O26' read as '2026-01-26'; line_items[1].amount: '$3,500.O0' read as '3500.00' | rules |
| F3 | DUPLICATE | reject | Same vendor, lines and total as INV 1012 (PAID) | check_duplicate |

## Tool calls

| by | tool | args | result |
|---|---|---|---|
| validator | resolve_item | {"line": 1} | {"line": 1, "description": "Widget A", "item": "WidgetA", "match": "normalized"} |
| validator | resolve_item | {"line": 2} | {"line": 2, "description": "WidgetB", "item": "WidgetB", "match": "exact"} |
| validator | resolve_item | {"line": 3} | {"line": 3, "description": "Gadget X", "item": "GadgetX", "match": "normalized"} |
| validator | check_totals | {} | {"lines_sum": 9500.0, "expected_total": 9975.0, "stated_total": 9975.0, "problems": [], "ok": true} |
| validator | check_duplicate | {} | {"result": "duplicate", "of": "INV 1012", "prior_status": "PAID"} |
| validator | get_vendor | {"name": "QuickShip Distributers"} | {"known": true, "name": "QuickShip Distributers", "aliases": ["FastShip Ltd."], "first_seen": "2021-07-01", "earlier_invoices": [{"number": "INV 1012", "total": |
| validator | check_stock | {"item": "WidgetA"} | {"item": "WidgetA", "lines": [1], "requested": 12.0, "in_stock": 15, "ok": true} |
| validator | check_stock | {"item": "WidgetB"} | {"item": "WidgetB", "lines": [2], "requested": 7.0, "in_stock": 10, "ok": true} |
| validator | check_stock | {"item": "GadgetX"} | {"item": "GadgetX", "lines": [3], "requested": 4.0, "in_stock": 5, "ok": true} |
| validator | check_price | {"line": 1} | {"line": 1, "item": "WidgetA", "invoiced": 250.0, "catalog": 250.0, "variance_pct": 0.0, "within_tolerance": true} |
| validator | check_price | {"line": 2} | {"line": 2, "item": "WidgetB", "invoiced": 500.0, "catalog": 500.0, "variance_pct": 0.0, "within_tolerance": true} |
| validator | check_price | {"line": 3} | {"line": 3, "item": "GadgetX", "invoiced": 750.0, "catalog": 750.0, "variance_pct": 0.0, "within_tolerance": true} |
| risk | get_vendor | {"name": "QuickShip Distributers"} | {"known": true, "name": "QuickShip Distributers", "aliases": ["FastShip Ltd."], "first_seen": "2021-07-01", "earlier_invoices": [{"number": "INV 1012", "total": |
| risk | get_vendor | {"name": "FastShip Ltd."} | {"known": true, "name": "QuickShip Distributers", "aliases": ["FastShip Ltd."], "first_seen": "2021-07-01", "earlier_invoices": []} |
| approver | get_vendor | {"name": "QuickShip Distributers"} | {"known": true, "name": "QuickShip Distributers", "aliases": ["FastShip Ltd."], "first_seen": "2021-07-01", "earlier_invoices": [{"number": "INV 1012", "total": |

## Validator notes

```json
{
  "checks_run": [
    "resolve_item(1)",
    "resolve_item(2)",
    "resolve_item(3)",
    "check_stock(WidgetA)",
    "check_stock(WidgetB)",
    "check_stock(GadgetX)",
    "check_price(1)",
    "check_price(2)",
    "check_price(3)",
    "check_totals",
    "check_duplicate",
    "get_vendor(QuickShip Distributers)"
  ],
  "concerns": [
    "Notes cite PO-20260115, which no tool verified against a purchase order.",
    "Shipping is null rather than an explicit amount; totals still matched without a shipping charge.",
    "After this invoice, stock headroom is thin even though check_stock was ok: WidgetA 12 of 15 and GadgetX 4 of 5.",
    "Vendor master alias FastShip Ltd. is on file; the invoice uses the canonical name QuickShip Distributers, so pay the master record rather than the alias."
  ],
  "summary": "All three lines matched the catalog (WidgetA, WidgetB, GadgetX); prices, stock, and stated totals checked out. check_duplicate reports this is a resubmission of INV 1012, already PAID for the same $9975.00."
}
```

## Risk memo

```json
{
  "level": "low",
  "signals": [],
  "summary": "The “formerly FastShip Ltd.” line matches a known vendor alias, so it is not an unexplained vendor change. Nothing else on the document suggests deception beyond the automated duplicate and near-threshold findings."
}
```

## VP draft 1

```json
{
  "action": "reject",
  "reasons": [
    {
      "text": "F3 is a reject-severity duplicate: this document is the same vendor, lines, and total as INV 1012, which vendor master shows already PAID. The payment gate blocks it; do not pay again.",
      "finding_ids": [
        "F3"
      ]
    },
    {
      "text": "F1 is info only. The $9,975 total sits just under the $10,000 line, so it does not by itself require the over-threshold write-up, and it does not offset the duplicate.",
      "finding_ids": [
        "F1"
      ]
    },
    {
      "text": "F2 is info only. OCR fixes (date 26-Jan-2O26 to 2026-01-26; line amount $3,500.O0 to 3500.00) are transcription normalizations and do not create a new payable.",
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
  "summary": "Reject. INV 1012 from QuickShip Distributers ($9,975) is already paid; this is the same invoice, so it must not be paid again. Near-threshold and OCR notes are informational only, and the risk memo is low."
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
  "reasoning": "F3 is a reject-severity duplicate: this document matches already-paid INV 1012 from QuickShip Distributers on vendor, lines, and total 9,975.00, so it must not be paid again or returned for resubmission. F1 (total just under the 10,000 approval line) and F2 (OCR normalizations of the invoice date and a line amount) are informational only and do not create a new payable or offset the duplicate. Disposition is void.",
  "vendor_reply": null
}
```
