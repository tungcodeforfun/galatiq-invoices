# invoice_1005.json: REJECTED (return_to_vendor)

Finding F1 rejects INV-1005 because the GadgetX line requests 8 units, which exceeds the 5 units in stock. Quantities over what we can accept are returned so the vendor can correct and resubmit. No duplicate, corrupt data, or fraud finding supports a void.

Run `20261125-033438-invoice_1005-c31f` · seconds 202.6 · llm_calls 11 · tool_calls 13 · tiers ['live'] · tokens 29636 · cost_usd 0.0427

## Extracted invoice

| field | value |
|---|---|
| invoice_number | INV-1005 |
| vendor | Global Supply Chain Partners |
| invoice_date | 2026-01-18 |
| due_date | 2026-03-18 |
| due_date_as_written | 2026-03-18 |
| currency | USD |
| subtotal | 14500.0 |
| tax | 725.0 |
| shipping | None |
| total | 15225.0 |
| payment_terms | Net 60 |
| notes | None |
| revision | None |

| # | description | qty | unit price | amount | note |
|---|---|---|---|---|---|
| 1 | WidgetA | 14.0 | 250.0 | None |  |
| 2 | GadgetX | 8.0 | 750.0 | None |  |
| 3 | WidgetB | 10.0 | 500.0 | None |  |

## Findings

| id | code | severity | message | source |
|---|---|---|---|---|
| F1 | STOCK_EXCEEDED | reject | GadgetX: 8 requested across 1 line(s), 5 in stock | check_stock |

## Tool calls

| by | tool | args | result |
|---|---|---|---|
| validator | resolve_item | {"line": 1} | {"line": 1, "description": "WidgetA", "item": "WidgetA", "match": "exact"} |
| validator | resolve_item | {"line": 2} | {"line": 2, "description": "GadgetX", "item": "GadgetX", "match": "exact"} |
| validator | resolve_item | {"line": 3} | {"line": 3, "description": "WidgetB", "item": "WidgetB", "match": "exact"} |
| validator | check_totals | {} | {"lines_sum": 14500.0, "expected_total": 15225.0, "stated_total": 15225.0, "problems": [], "ok": true} |
| validator | check_duplicate | {} | {"result": "no_match"} |
| validator | get_vendor | {"name": "Global Supply Chain Partners"} | {"known": true, "name": "Global Supply Chain Partners", "aliases": [], "first_seen": "2024-02-19", "earlier_invoices": []} |
| validator | check_stock | {"item": "WidgetA"} | {"item": "WidgetA", "lines": [1], "requested": 14.0, "in_stock": 15, "ok": true} |
| validator | check_stock | {"item": "GadgetX"} | {"item": "GadgetX", "lines": [2], "requested": 8.0, "in_stock": 5, "ok": false} |
| validator | check_stock | {"item": "WidgetB"} | {"item": "WidgetB", "lines": [3], "requested": 10.0, "in_stock": 10, "ok": true} |
| validator | check_price | {"line": 1} | {"line": 1, "item": "WidgetA", "invoiced": 250.0, "catalog": 250.0, "variance_pct": 0.0, "within_tolerance": true} |
| validator | check_price | {"line": 2} | {"line": 2, "item": "GadgetX", "invoiced": 750.0, "catalog": 750.0, "variance_pct": 0.0, "within_tolerance": true} |
| validator | check_price | {"line": 3} | {"line": 3, "item": "WidgetB", "invoiced": 500.0, "catalog": 500.0, "variance_pct": 0.0, "within_tolerance": true} |
| risk | get_vendor | {"name": "Global Supply Chain Partners"} | {"known": true, "name": "Global Supply Chain Partners", "aliases": [], "first_seen": "2024-02-19", "earlier_invoices": []} |

## Validator notes

```json
{
  "checks_run": [
    "resolve_item(line=1)",
    "resolve_item(line=2)",
    "resolve_item(line=3)",
    "check_stock(WidgetA)",
    "check_stock(GadgetX)",
    "check_stock(WidgetB)",
    "check_price(line=1)",
    "check_price(line=2)",
    "check_price(line=3)",
    "check_totals",
    "check_duplicate",
    "get_vendor(Global Supply Chain Partners)"
  ],
  "concerns": [
    "Line amounts and shipping are blank on the invoice. check_totals still reconciled the stated total, which is consistent with shipping treated as zero; confirm shipping was intentionally omitted rather than omitted in extraction.",
    "Vendor master lists Global Supply Chain Partners as known since 2024-02-19 with no aliases and no earlier invoices on this ledger, so there is no prior payment history here to compare."
  ],
  "summary": "INV-1005 from Global Supply Chain Partners was checked on all three lines (WidgetA, GadgetX, WidgetB), stock, prices, totals, duplicates, and the vendor master. Prices, totals, and duplicate lookup were clean and the vendor is known; check_stock flagged GadgetX (8 requested, 5 on hand)."
}
```

## Risk memo

```json
{
  "level": "medium",
  "signals": [
    {
      "kind": "other",
      "quote": "1600 Pennsylvania Ave, Washington, DC 20500",
      "why": "A commercial supplier listing the White House as its address is inconsistent with a legitimate business remit-to and suggests the document may be fabricated."
    }
  ],
  "summary": "The vendor name is on the master, but the invoice address is the White House, which does not fit a real supplier and is not explained by aliases or prior invoices. No payment redirect, pressure language, or instruction to the approver appears; weigh the address before paying."
}
```

## VP draft 1

```json
{
  "action": "reject",
  "reasons": [
    {
      "text": "F1 is a reject-severity stock check: GadgetX quantity 8 exceeds the 5 units in stock. The payment gate blocks this invoice, so it cannot be paid.",
      "finding_ids": [
        "F1"
      ]
    },
    {
      "text": "Amount is $15,225, over the $10,000 scrutiny threshold. Line math reconciles (14×250 + 8×750 + 10×500 = 14,500 subtotal; tax 725; total 15,225) with blank shipping treated as zero, but that does not clear F1.",
      "finding_ids": [
        "F1"
      ]
    },
    {
      "text": "Medium risk memo: remit-to is 1600 Pennsylvania Ave, Washington, DC 20500 (the White House), which is not a plausible commercial supplier address. Vendor is on file since 2024-02-19 with no aliases and no prior invoices, so the address is unexplained. The memo alone would not outweigh clean checks, but checks did not pass, and the address on the document is an independent reason not to pay.",
      "finding_ids": []
    }
  ],
  "addressed_findings": [
    "F1"
  ],
  "summary": "Reject INV-1005 for $15,225. F1 blocks payment because GadgetX quantity exceeds stock, and the White House remit-to in the medium risk memo is not a credible supplier address."
}
```

## Critique 1

```json
{
  "verdict": "revise",
  "objections": [
    "The claim that the medium risk memo's White House remit-to \"is an independent reason not to pay\" is not supported. Memo level is medium, not high, and a medium memo alone is not grounds to refuse a vendor on file (Global Supply Chain Partners, known since 2024-02-19). Rejection is supported only by F1."
  ]
}
```

## VP draft 2

```json
{
  "action": "reject",
  "reasons": [
    {
      "text": "F1 is a reject-severity stock check: GadgetX quantity 8 exceeds the 5 units in stock. The payment gate blocks this invoice, so it cannot be paid.",
      "finding_ids": [
        "F1"
      ]
    },
    {
      "text": "Amount is $15,225, over the $10,000 scrutiny threshold. Line math reconciles (14×250 + 8×750 + 10×500 = 14,500 subtotal; tax 725; total 15,225) with blank shipping treated as zero. That does not clear F1.",
      "finding_ids": [
        "F1"
      ]
    },
    {
      "text": "Medium risk memo (White House remit-to, 1600 Pennsylvania Ave) is noted and weighed. It is not high, and it is not an independent ground to refuse Global Supply Chain Partners, on file since 2024-02-19 with no aliases. Rejection rests only on F1.",
      "finding_ids": [
        "F1"
      ]
    }
  ],
  "addressed_findings": [
    "F1"
  ],
  "summary": "Reject INV-1005 for $15,225 solely because F1 blocks payment: GadgetX quantity exceeds stock. The medium risk memo is noted and does not add a separate refusal ground."
}
```

## Critique 2

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
  "reasoning": "Finding F1 rejects INV-1005 because the GadgetX line requests 8 units, which exceeds the 5 units in stock. Quantities over what we can accept are returned so the vendor can correct and resubmit. No duplicate, corrupt data, or fraud finding supports a void.",
  "vendor_reply": "Hello Global Supply Chain Partners billing team, we cannot accept invoice INV-1005 as submitted. The GadgetX line shows a quantity of 8, which is more than we can accept. Please resubmit a corrected invoice with an acceptable GadgetX quantity and with the line amount, subtotal, tax, and total recalculated to match. Thank you."
}
```
