# invoice_1007.csv: REJECTED (return_to_vendor)

INV-1007 is rejected under F1 because line items plus tax equal 15,635.00 while the stated total is 15,525.00, short by 110.00. F2 and F3 show WidgetA quantity 20 exceeds the 15 units in stock and WidgetB quantity 15 exceeds the 10 units in stock. These are correctable defects (wrong total and quantities over what we can accept), so the invoice is returned to the vendor rather than voided.

Run `20261125-034040-invoice_1007-ef5a` · seconds 101.6 · llm_calls 8 · tool_calls 12 · tiers ['live'] · tokens 22100 · cost_usd 0.0245

## Extracted invoice

| field | value |
|---|---|
| invoice_number | INV-1007 |
| vendor | MegaWidgets Corp |
| invoice_date | 2026-01-28 |
| due_date | 2026-02-28 |
| due_date_as_written | 02/28/2026 |
| currency | None |
| subtotal | 14750.0 |
| tax | 885.0 |
| shipping | None |
| total | 15525.0 |
| payment_terms | None |
| notes | None |
| revision | None |

| # | description | qty | unit price | amount | note |
|---|---|---|---|---|---|
| 1 | WidgetA | 20.0 | 250.0 | 5000.0 |  |
| 2 | WidgetB | 15.0 | 500.0 | 7500.0 |  |
| 3 | GadgetX | 3.0 | 750.0 | 2250.0 |  |

## Findings

| id | code | severity | message | source |
|---|---|---|---|---|
| F1 | TOTAL_MISMATCH | reject | lines + tax + shipping = 15,635.00, total says 15,525.00 (-110.00) | check_totals |
| F2 | STOCK_EXCEEDED | reject | WidgetA: 20 requested across 1 line(s), 15 in stock | check_stock |
| F3 | STOCK_EXCEEDED | reject | WidgetB: 15 requested across 1 line(s), 10 in stock | check_stock |

## Tool calls

| by | tool | args | result |
|---|---|---|---|
| validator | resolve_item | {"line": 1} | {"line": 1, "description": "WidgetA", "item": "WidgetA", "match": "exact"} |
| validator | resolve_item | {"line": 2} | {"line": 2, "description": "WidgetB", "item": "WidgetB", "match": "exact"} |
| validator | resolve_item | {"line": 3} | {"line": 3, "description": "GadgetX", "item": "GadgetX", "match": "exact"} |
| validator | check_totals | {} | {"lines_sum": 14750.0, "expected_total": 15635.0, "stated_total": 15525.0, "problems": ["lines + tax + shipping = 15,635.00, total says 15,525.00 (-110.00)"], " |
| validator | check_duplicate | {} | {"result": "no_match"} |
| validator | get_vendor | {"name": "MegaWidgets Corp"} | {"known": true, "name": "MegaWidgets Corp", "aliases": [], "first_seen": "2024-05-02", "earlier_invoices": []} |
| validator | check_stock | {"item": "WidgetA"} | {"item": "WidgetA", "lines": [1], "requested": 20.0, "in_stock": 15, "ok": false} |
| validator | check_stock | {"item": "WidgetB"} | {"item": "WidgetB", "lines": [2], "requested": 15.0, "in_stock": 10, "ok": false} |
| validator | check_stock | {"item": "GadgetX"} | {"item": "GadgetX", "lines": [3], "requested": 3.0, "in_stock": 5, "ok": true} |
| validator | check_price | {"line": 1} | {"line": 1, "item": "WidgetA", "invoiced": 250.0, "catalog": 250.0, "variance_pct": 0.0, "within_tolerance": true} |
| validator | check_price | {"line": 2} | {"line": 2, "item": "WidgetB", "invoiced": 500.0, "catalog": 500.0, "variance_pct": 0.0, "within_tolerance": true} |
| validator | check_price | {"line": 3} | {"line": 3, "item": "GadgetX", "invoiced": 750.0, "catalog": 750.0, "variance_pct": 0.0, "within_tolerance": true} |

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
    "get_vendor(MegaWidgets Corp)"
  ],
  "concerns": [
    "Currency is null, so amounts are not tied to a stated currency.",
    "Shipping is null; line math (20×250, 15×500, 3×750) matches the stated subtotal of 14,750.00 and tax is 885.00, but the stated total is 110.00 below subtotal plus tax.",
    "Vendor is known since 2024-05-02, yet the ledger lists no earlier invoices for it."
  ],
  "summary": "All three lines matched the catalog at catalog prices, and this is not a duplicate. Tools flagged insufficient stock for WidgetA (20 requested, 15 on hand) and WidgetB (15 requested, 10 on hand), and a total that is 110.00 below lines plus tax plus shipping (15,525.00 stated vs 15,635.00 expected). GadgetX stock is sufficient."
}
```

## Risk memo

```json
{
  "level": "low",
  "signals": [],
  "summary": "The invoice is a plain MegaWidgets Corp bill with no pressure language, payment-redirect, instruction injection, or conflicting vendor identity. Nothing beyond the automated total and stock findings warrants a fraud hold."
}
```

## VP draft 1

```json
{
  "action": "reject",
  "reasons": [
    {
      "text": "F1 is a reject-severity total mismatch: line items plus tax equal 15,635.00 (subtotal 14,750.00 + tax 885.00; shipping null), but the invoice total is 15,525.00, short by 110.00. A reject finding blocks payment.",
      "finding_ids": [
        "F1"
      ]
    },
    {
      "text": "F2 is a reject-severity stock exceedance: WidgetA quantity 20 exceeds the 15 units in stock, so the line cannot be fulfilled as billed.",
      "finding_ids": [
        "F2"
      ]
    },
    {
      "text": "F3 is a reject-severity stock exceedance: WidgetB quantity 15 exceeds the 10 units in stock, so that line also cannot be fulfilled as billed.",
      "finding_ids": [
        "F3"
      ]
    },
    {
      "text": "Amount is over $10,000 (stated total 15,525.00). The risk memo is low with no fraud signals (no pressure language, payment redirect, or conflicting vendor identity) and does not itself require a fraud hold, but it does not override the three reject findings. Currency is unstated and there are no prior invoices on file; neither changes the total or stock defects already shown on the document.",
      "finding_ids": [
        "F1",
        "F2",
        "F3"
      ]
    }
  ],
  "addressed_findings": [
    "F1",
    "F2",
    "F3"
  ],
  "summary": "Reject INV-1007. The stated total is 110.00 below lines plus tax, and WidgetA and WidgetB quantities both exceed stock; those reject findings block payment despite a low risk memo."
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
  "disposition": "return_to_vendor",
  "reasoning": "INV-1007 is rejected under F1 because line items plus tax equal 15,635.00 while the stated total is 15,525.00, short by 110.00. F2 and F3 show WidgetA quantity 20 exceeds the 15 units in stock and WidgetB quantity 15 exceeds the 10 units in stock. These are correctable defects (wrong total and quantities over what we can accept), so the invoice is returned to the vendor rather than voided.",
  "vendor_reply": "Hello MegaWidgets Corp billing team,\n\nWe cannot process invoice INV-1007 as submitted. Line amounts plus tax equal 15,635.00 (subtotal 14,750.00 + tax 885.00; no shipping stated), but the invoice total is 15,525.00, which is 110.00 short. Please resubmit a corrected invoice whose total equals the sum of the line amounts, tax, and any shipping.\n\nWidgetA is billed at quantity 20 and WidgetB at quantity 15, both of which exceed the quantities we can accept. Please reduce those quantities and include the revised quantities and amounts on the corrected invoice.\n\nThank you,\nAcme Corp Accounts Payable"
}
```
