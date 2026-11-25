# invoice_3008.txt: REJECTED (return_to_vendor)

INV-3008 is rejected under F1 because the stated total does not match the document math. Line amounts 2,250.00 and 500.00 plus tax 220.00 equal 2,970.00, while the invoice total is 3,170.00 (200.00 higher) and shipping is null. A total mismatch is correctable by the vendor, so policy requires return_to_vendor rather than void.

Run `20261125-034411-invoice_3008-e287` · seconds 58.3 · llm_calls 8 · tool_calls 9 · tiers ['live'] · tokens 20569 · cost_usd 0.0176

## Extracted invoice

| field | value |
|---|---|
| invoice_number | INV-3008 |
| vendor | Atlas Industrial Supply |
| invoice_date | 2026-02-13 |
| due_date | 2026-03-15 |
| due_date_as_written | 2026-03-15 |
| currency | USD |
| subtotal | 2750.0 |
| tax | 220.0 |
| shipping | None |
| total | 3170.0 |
| payment_terms | Net 30 |
| notes | None |
| revision | None |

| # | description | qty | unit price | amount | note |
|---|---|---|---|---|---|
| 1 | GadgetX | 3.0 | 750.0 | 2250.0 |  |
| 2 | WidgetA | 2.0 | 250.0 | 500.0 |  |

## Findings

| id | code | severity | message | source |
|---|---|---|---|---|
| F1 | TOTAL_MISMATCH | reject | lines + tax + shipping = 2,970.00, total says 3,170.00 (+200.00) | check_totals |

## Tool calls

| by | tool | args | result |
|---|---|---|---|
| validator | resolve_item | {"line": 1} | {"line": 1, "description": "GadgetX", "item": "GadgetX", "match": "exact"} |
| validator | resolve_item | {"line": 2} | {"line": 2, "description": "WidgetA", "item": "WidgetA", "match": "exact"} |
| validator | check_totals | {} | {"lines_sum": 2750.0, "expected_total": 2970.0, "stated_total": 3170.0, "problems": ["lines + tax + shipping = 2,970.00, total says 3,170.00 (+200.00)"], "ok":  |
| validator | check_duplicate | {} | {"result": "no_match"} |
| validator | get_vendor | {"name": "Atlas Industrial Supply"} | {"known": true, "name": "Atlas Industrial Supply", "aliases": [], "first_seen": "2024-08-09", "earlier_invoices": []} |
| validator | check_stock | {"item": "GadgetX"} | {"item": "GadgetX", "lines": [1], "requested": 3.0, "in_stock": 5, "ok": true} |
| validator | check_stock | {"item": "WidgetA"} | {"item": "WidgetA", "lines": [2], "requested": 2.0, "in_stock": 15, "ok": true} |
| validator | check_price | {"line": 1} | {"line": 1, "item": "GadgetX", "invoiced": 750.0, "catalog": 750.0, "variance_pct": 0.0, "within_tolerance": true} |
| validator | check_price | {"line": 2} | {"line": 2, "item": "WidgetA", "invoiced": 250.0, "catalog": 250.0, "variance_pct": 0.0, "within_tolerance": true} |

## Validator notes

```json
{
  "checks_run": [
    "resolve_item(1)",
    "resolve_item(2)",
    "check_stock(GadgetX)",
    "check_stock(WidgetA)",
    "check_price(1)",
    "check_price(2)",
    "check_totals",
    "check_duplicate",
    "get_vendor(Atlas Industrial Supply)"
  ],
  "concerns": [
    "Shipping is null, so the tool's expected total is 2,970.00. The stated total of 3,170.00 is exactly 200.00 higher, which is consistent with an unitemized shipping charge folded into the total rather than a random arithmetic error.",
    "Vendor is known (first seen 2024-08-09) but the master lists no earlier invoices, so there is no payment history to compare against."
  ],
  "summary": "Both lines matched the catalog exactly (GadgetX, WidgetA); stock and unit prices are within tolerance, and the invoice is not a duplicate. check_totals failed: lines plus tax (shipping null) equal 2,970.00, but the invoice states 3,170.00."
}
```

## Risk memo

```json
{
  "level": "low",
  "signals": [],
  "summary": "No fraud or manipulation signals beyond the automated total mismatch. The invoice is ordinary commercial wording with no pressure, payment redirect, instruction injection, or conflicting vendor identity."
}
```

## VP draft 1

```json
{
  "action": "reject",
  "reasons": [
    {
      "text": "F1 is a reject-severity total mismatch: line items 2,250.00 + 500.00 plus tax 220.00 equal 2,970.00, but the invoice total is 3,170.00 (200.00 higher, shipping null). A reject finding blocks payment regardless of the low risk memo or the known vendor.",
      "finding_ids": [
        "F1"
      ]
    }
  ],
  "addressed_findings": [
    "F1"
  ],
  "summary": "Do not pay INV-3008. The stated total is $200.00 above lines plus tax, and that reject-severity mismatch blocks payment."
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
  "reasoning": "INV-3008 is rejected under F1 because the stated total does not match the document math. Line amounts 2,250.00 and 500.00 plus tax 220.00 equal 2,970.00, while the invoice total is 3,170.00 (200.00 higher) and shipping is null. A total mismatch is correctable by the vendor, so policy requires return_to_vendor rather than void.",
  "vendor_reply": "Hello Atlas Industrial Supply billing team,\n\nWe cannot process invoice INV-3008 (dated 2026-02-13) because the total does not match the other amounts on the invoice. Line items are 2,250.00 and 500.00 (subtotal 2,750.00) and tax is 220.00, which sum to 2,970.00, but the invoice total is 3,170.00 — 200.00 higher. Shipping is not shown.\n\nPlease resubmit a corrected invoice in which the total equals the line amounts plus tax plus any shipping, with those figures shown clearly.\n\nThank you."
}
```
