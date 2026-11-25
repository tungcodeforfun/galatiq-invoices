# invoice_1005.json: REJECTED (return_to_vendor)

Finding F1 rejects INV-1005 because GadgetX is billed for 8 units against 5 in stock, a quantity over what we can accept. Policy requires return_to_vendor for F1 so the vendor can correct that quantity and resubmit. The invoice is not voided: F1 is correctable, and there is no duplicate, corrupt-data, or fraud finding.

Run `20261125-014054-invoice_1005-ef25` · seconds 108.6 · llm_calls 10 · tool_calls 14 · tiers ['live'] · tokens 26365 · cost_usd 0.0276

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
| approver | get_vendor | {"name": "Global Supply Chain Partners"} | {"known": true, "name": "Global Supply Chain Partners", "aliases": [], "first_seen": "2024-02-19", "earlier_invoices": []} |

## Validator notes

```json
{
  "checks_run": [
    "resolve_item(line 1)",
    "resolve_item(line 2)",
    "resolve_item(line 3)",
    "check_stock(WidgetA)",
    "check_stock(GadgetX)",
    "check_stock(WidgetB)",
    "check_price(line 1)",
    "check_price(line 2)",
    "check_price(line 3)",
    "check_totals",
    "check_duplicate",
    "get_vendor(Global Supply Chain Partners)"
  ],
  "concerns": [
    "GadgetX is short: invoice asks for 8 and stock is 5; the stock check already marks this not ok.",
    "WidgetB uses the full on-hand quantity (10 of 10), so the line is within stock but leaves no buffer.",
    "Line amounts and shipping are blank on the extract; totals still reconciled (lines 14500, tax 725, stated total 15225).",
    "Vendor is known (first seen 2024-02-19) but has no earlier invoices and no aliases."
  ],
  "summary": "All three lines matched the catalog exactly, prices were within tolerance, totals matched, and the invoice is not a duplicate. The only tool failure is GadgetX stock: 8 requested against 5 on hand."
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
      "why": "A commercial supplier listing the White House as its address is inconsistent with a real business location and may indicate a fabricated identity."
    }
  ],
  "summary": "The vendor is known in the master since 2024, with no payment-redirect, pressure, or instruction text. The street address is the White House, which the VP should weigh before paying."
}
```

## VP draft 1

```json
{
  "action": "reject",
  "reasons": [
    {
      "text": "F1 is a reject-severity stock check: GadgetX is billed for 8 units but only 5 are in stock. That finding blocks payment regardless of other factors.",
      "finding_ids": [
        "F1"
      ]
    },
    {
      "text": "Invoice total is $15,225, so the medium risk memo is weighed explicitly. The memo flags a White House street address as inconsistent with a commercial supplier. The vendor is on file since 2024-02-19 with no aliases, no earlier invoices, and no payment-redirect or pressure language. A medium memo alone would not outweigh a vendor whose checks all pass, but they do not: F1 already requires rejection, and the address inconsistency adds identity risk rather than clearing the stock failure.",
      "finding_ids": [
        "F1"
      ]
    }
  ],
  "addressed_findings": [
    "F1"
  ],
  "summary": "Reject INV-1005 ($15,225). GadgetX quantity exceeds stock (F1, reject severity), so the payment gate blocks this invoice. The medium White House-address memo is noted and does not change that result."
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
  ],
  "overridden": false
}
```

## Resolution

```json
{
  "disposition": "return_to_vendor",
  "reasoning": "Finding F1 rejects INV-1005 because GadgetX is billed for 8 units against 5 in stock, a quantity over what we can accept. Policy requires return_to_vendor for F1 so the vendor can correct that quantity and resubmit. The invoice is not voided: F1 is correctable, and there is no duplicate, corrupt-data, or fraud finding.",
  "vendor_reply": "Hello Global Supply Chain Partners billing team, we cannot process invoice INV-1005 as submitted. GadgetX is billed for a quantity of 8, which is more than we can accept. Please resubmit a corrected invoice with a lower GadgetX quantity and with the line amount, subtotal, tax, and total recalculated to match. Thank you."
}
```
