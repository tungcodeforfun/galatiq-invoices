# invoice_1013.pdf: REJECTED (void)

INV-1013 is voided because F2 identifies it as a duplicate of a previously rejected invoice with the same vendor, lines, and total, so it must not come back. F1 is a reject-severity total mismatch: lines plus tax equal 22,512.80 while the invoice total is 22,562.80. F3, F4, and F5 are reject-severity quantity overruns on WidgetA, WidgetB, and GadgetX.

Run `20261125-035339-invoice_1013-3728` · seconds 94.6 · llm_calls 10 · tool_calls 24 · tiers ['live'] · tokens 30773 · cost_usd 0.0305

## Extracted invoice

| field | value |
|---|---|
| invoice_number | INV-1013 |
| vendor | Atlas Industrial Supply |
| invoice_date | 2026-01-24 |
| due_date | 2026-03-24 |
| due_date_as_written | 2026-03-24 |
| currency | USD |
| subtotal | 21040.0 |
| tax | 1472.8 |
| shipping | None |
| total | 22562.8 |
| payment_terms | Net 60 |
| notes | None |
| revision | None |

| # | description | qty | unit price | amount | note |
|---|---|---|---|---|---|
| 1 | WidgetA | 15.0 | 250.0 | 3750.0 |  |
| 2 | WidgetB | 10.0 | 500.0 | 5000.0 |  |
| 3 | GadgetX | 5.0 | 750.0 | 3750.0 |  |
| 4 | WidgetA | 5.0 | 240.0 | 1200.0 | Volume discount |
| 5 | WidgetB | 8.0 | 480.0 | 3840.0 | Volume discount |
| 6 | GadgetX | 3.0 | 750.0 | 2250.0 | Expedited |
| 7 | WidgetA | 2.0 | 250.0 | 500.0 | Replacement |
| 8 | GadgetX | 1.0 | 750.0 | 750.0 | Sample |

## Findings

| id | code | severity | message | source |
|---|---|---|---|---|
| F1 | TOTAL_MISMATCH | reject | lines + tax + shipping = 22,512.80, total says 22,562.80 (+50.00) | check_totals |
| F2 | DUPLICATE | reject | Same vendor, lines and total as INV-1013 (REJECTED) | check_duplicate |
| F3 | STOCK_EXCEEDED | reject | WidgetA: 22 requested across 3 line(s), 15 in stock | check_stock |
| F4 | STOCK_EXCEEDED | reject | WidgetB: 18 requested across 2 line(s), 10 in stock | check_stock |
| F5 | STOCK_EXCEEDED | reject | GadgetX: 9 requested across 3 line(s), 5 in stock | check_stock |

## Tool calls

| by | tool | args | result |
|---|---|---|---|
| validator | resolve_item | {"line": 1} | {"line": 1, "description": "WidgetA", "item": "WidgetA", "match": "exact"} |
| validator | resolve_item | {"line": 2} | {"line": 2, "description": "WidgetB", "item": "WidgetB", "match": "exact"} |
| validator | resolve_item | {"line": 3} | {"line": 3, "description": "GadgetX", "item": "GadgetX", "match": "exact"} |
| validator | resolve_item | {"line": 4} | {"line": 4, "description": "WidgetA", "item": "WidgetA", "match": "exact"} |
| validator | resolve_item | {"line": 5} | {"line": 5, "description": "WidgetB", "item": "WidgetB", "match": "exact"} |
| validator | resolve_item | {"line": 6} | {"line": 6, "description": "GadgetX", "item": "GadgetX", "match": "exact"} |
| validator | resolve_item | {"line": 7} | {"line": 7, "description": "WidgetA", "item": "WidgetA", "match": "exact"} |
| validator | resolve_item | {"line": 8} | {"line": 8, "description": "GadgetX", "item": "GadgetX", "match": "exact"} |
| validator | check_totals | {} | {"lines_sum": 21040.0, "expected_total": 22512.8, "stated_total": 22562.8, "problems": ["lines + tax + shipping = 22,512.80, total says 22,562.80 (+50.00)"], "o |
| validator | check_duplicate | {} | {"result": "duplicate", "of": "INV-1013", "prior_status": "REJECTED"} |
| validator | get_vendor | {"name": "Atlas Industrial Supply"} | {"known": true, "name": "Atlas Industrial Supply", "aliases": [], "first_seen": "2024-08-09", "earlier_invoices": [{"number": "INV-1013", "total": 22562.8, "sta |
| validator | check_stock | {"item": "WidgetA"} | {"item": "WidgetA", "lines": [1, 4, 7], "requested": 22.0, "in_stock": 15, "ok": false} |
| validator | check_stock | {"item": "WidgetB"} | {"item": "WidgetB", "lines": [2, 5], "requested": 18.0, "in_stock": 10, "ok": false} |
| validator | check_stock | {"item": "GadgetX"} | {"item": "GadgetX", "lines": [3, 6, 8], "requested": 9.0, "in_stock": 5, "ok": false} |
| validator | check_price | {"line": 1} | {"line": 1, "item": "WidgetA", "invoiced": 250.0, "catalog": 250.0, "variance_pct": 0.0, "within_tolerance": true} |
| validator | check_price | {"line": 2} | {"line": 2, "item": "WidgetB", "invoiced": 500.0, "catalog": 500.0, "variance_pct": 0.0, "within_tolerance": true} |
| validator | check_price | {"line": 3} | {"line": 3, "item": "GadgetX", "invoiced": 750.0, "catalog": 750.0, "variance_pct": 0.0, "within_tolerance": true} |
| validator | check_price | {"line": 4} | {"line": 4, "item": "WidgetA", "invoiced": 240.0, "catalog": 250.0, "variance_pct": -4.0, "within_tolerance": true} |
| validator | check_price | {"line": 5} | {"line": 5, "item": "WidgetB", "invoiced": 480.0, "catalog": 500.0, "variance_pct": -4.0, "within_tolerance": true} |
| validator | check_price | {"line": 6} | {"line": 6, "item": "GadgetX", "invoiced": 750.0, "catalog": 750.0, "variance_pct": 0.0, "within_tolerance": true} |
| validator | check_price | {"line": 7} | {"line": 7, "item": "WidgetA", "invoiced": 250.0, "catalog": 250.0, "variance_pct": 0.0, "within_tolerance": true} |
| validator | check_price | {"line": 8} | {"line": 8, "item": "GadgetX", "invoiced": 750.0, "catalog": 750.0, "variance_pct": 0.0, "within_tolerance": true} |
| risk | get_vendor | {"name": "Atlas Industrial Supply"} | {"known": true, "name": "Atlas Industrial Supply", "aliases": [], "first_seen": "2024-08-09", "earlier_invoices": [{"number": "INV-1013", "total": 22562.8, "sta |
| approver | get_vendor | {"name": "Atlas Industrial Supply"} | {"known": true, "name": "Atlas Industrial Supply", "aliases": [], "first_seen": "2024-08-09", "earlier_invoices": [{"number": "INV-1013", "total": 22562.8, "sta |

## Validator notes

```json
{
  "checks_run": [
    "resolve_item(1)",
    "resolve_item(2)",
    "resolve_item(3)",
    "resolve_item(4)",
    "resolve_item(5)",
    "resolve_item(6)",
    "resolve_item(7)",
    "resolve_item(8)",
    "check_stock(WidgetA)",
    "check_stock(WidgetB)",
    "check_stock(GadgetX)",
    "check_price(1)",
    "check_price(2)",
    "check_price(3)",
    "check_price(4)",
    "check_price(5)",
    "check_price(6)",
    "check_price(7)",
    "check_price(8)",
    "check_totals",
    "check_duplicate",
    "get_vendor(Atlas Industrial Supply)"
  ],
  "concerns": [
    "Same invoice number and stated total as the earlier REJECTED INV-1013 (return_to_vendor), and revision is null, so this looks like an uncorrected resubmission rather than a revised bill.",
    "Line notes were not judged by the tools: line 8 is billed as a Sample at full catalog price, lines 4 and 7 mix a volume-discount price with full price on WidgetA, and line 6 is marked Expedited while shipping is null — the unexplained +50.00 on the total is not itemized."
  ],
  "summary": "All eight lines matched catalog items exactly. Stock is short on WidgetA, WidgetB, and GadgetX once quantities are summed; unit prices are within tolerance; the stated total is $50.00 high; and INV-1013 is a duplicate of a previously rejected invoice."
}
```

## Risk memo

```json
{
  "level": "low",
  "signals": [],
  "summary": "The invoice text shows no pressure language, payment redirection, reviewer instructions, or conflicting vendor identity. Nothing here suggests deception beyond the automated findings."
}
```

## VP draft 1

```json
{
  "action": "reject",
  "reasons": [
    {
      "text": "F1 is a reject-severity total mismatch: line items sum to 21,040.00 plus tax 1,472.80 equals 22,512.80, but the invoice total is 22,562.80. Shipping is null, so the extra 50.00 is not itemized and the bill is not payable as written.",
      "finding_ids": [
        "F1"
      ]
    },
    {
      "text": "F2 is a reject-severity duplicate. Vendor master shows Atlas Industrial Supply on file since 2024-08-09, and earlier INV-1013 for the same 22,562.80 was REJECTED and returned to vendor. Revision is null, so this is an uncorrected resubmission of the same invoice number, lines, and total.",
      "finding_ids": [
        "F2"
      ]
    },
    {
      "text": "F3, F4, and F5 are reject-severity stock overruns: WidgetA 22 requested vs 15 in stock, WidgetB 18 vs 10, and GadgetX 9 vs 5. Quantities exceed available stock on every product.",
      "finding_ids": [
        "F3",
        "F4",
        "F5"
      ]
    },
    {
      "text": "The risk memo is low and reports no pressure language, payment redirection, or vendor-identity conflict. That low memo, and the vendor being on file, does not outweigh five reject findings on an invoice over $10,000. The payment gate would block this regardless.",
      "finding_ids": [
        "F1",
        "F2",
        "F3",
        "F4",
        "F5"
      ]
    }
  ],
  "addressed_findings": [
    "F1",
    "F2",
    "F3",
    "F4",
    "F5"
  ],
  "summary": "Reject INV-1013 from Atlas Industrial Supply for 22,562.80. It is an uncorrected resubmission of a previously returned invoice, the total is 50.00 over lines plus tax, and all three products exceed stock."
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
  "reasoning": "INV-1013 is voided because F2 identifies it as a duplicate of a previously rejected invoice with the same vendor, lines, and total, so it must not come back. F1 is a reject-severity total mismatch: lines plus tax equal 22,512.80 while the invoice total is 22,562.80. F3, F4, and F5 are reject-severity quantity overruns on WidgetA, WidgetB, and GadgetX.",
  "vendor_reply": null
}
```
