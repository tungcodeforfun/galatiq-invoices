# invoice_3009.csv: REJECTED (return_to_vendor)

INV-3009 is rejected under F1 because the stated total of $2,475.00 does not equal line amounts plus shipping. Lines are $2,500.00, tax is blank, and shipping is $75.00, which sums to $2,575.00, a $100.00 shortfall with no documented discount. A corrected invoice can be resubmitted, so the disposition is return_to_vendor.

Run `20261125-034511-invoice_3009-b98f` · seconds 77.8 · llm_calls 9 · tool_calls 7 · tiers ['live'] · tokens 22330 · cost_usd 0.0198

## Extracted invoice

| field | value |
|---|---|
| invoice_number | INV-3009 |
| vendor | TechParts International |
| invoice_date | 2026-02-16 |
| due_date | 2026-03-18 |
| due_date_as_written | None |
| currency | USD |
| subtotal | 2500.0 |
| tax | None |
| shipping | 75.0 |
| total | 2475.0 |
| payment_terms | Net 30 |
| notes | None |
| revision | None |

| # | description | qty | unit price | amount | note |
|---|---|---|---|---|---|
| 1 | WidgetA | 10.0 | 250.0 | 2500.0 |  |

## Findings

| id | code | severity | message | source |
|---|---|---|---|---|
| F1 | TOTAL_MISMATCH | reject | lines + tax + shipping = 2,575.00, total says 2,475.00 (-100.00) | check_totals |

## Tool calls

| by | tool | args | result |
|---|---|---|---|
| validator | resolve_item | {"line": 1} | {"line": 1, "description": "WidgetA", "item": "WidgetA", "match": "exact"} |
| validator | check_totals | {} | {"lines_sum": 2500.0, "expected_total": 2575.0, "stated_total": 2475.0, "problems": ["lines + tax + shipping = 2,575.00, total says 2,475.00 (-100.00)"], "ok":  |
| validator | check_duplicate | {} | {"result": "no_match"} |
| validator | get_vendor | {"name": "TechParts International"} | {"known": true, "name": "TechParts International", "aliases": [], "first_seen": "2025-01-15", "earlier_invoices": []} |
| validator | check_stock | {"item": "WidgetA"} | {"item": "WidgetA", "lines": [1], "requested": 10.0, "in_stock": 15, "ok": true} |
| validator | check_price | {"line": 1} | {"line": 1, "item": "WidgetA", "invoiced": 250.0, "catalog": 250.0, "variance_pct": 0.0, "within_tolerance": true} |
| risk | get_vendor | {"name": "TechParts International"} | {"known": true, "name": "TechParts International", "aliases": [], "first_seen": "2025-01-15", "earlier_invoices": []} |

## Validator notes

```json
{
  "checks_run": [
    "resolve_item(line=1)",
    "check_totals()",
    "check_duplicate()",
    "get_vendor(TechParts International)",
    "check_stock(WidgetA)",
    "check_price(line=1)"
  ],
  "concerns": [
    "Tax is null rather than an explicit amount, so the shortfall versus lines plus shipping is unclassified: omitted tax, an unstated discount, or a total transcription error.",
    "Vendor is on the master (first seen 2025-01-15) but has no earlier invoices in the ledger.",
    "due_date_as_written is null; only a parsed due date is present."
  ],
  "summary": "WidgetA matched the catalog; stock and unit price are within tolerance, and this is not a duplicate. Totals do not reconcile: lines plus shipping come to 2,575.00 while the invoice total is 2,475.00."
}
```

## Risk memo

```json
{
  "level": "low",
  "signals": [],
  "summary": "Vendor TechParts International is on the master with no aliases or prior invoices, and the document has no pressure language, payment redirect, instruction injection, or conflicting vendor identity. Nothing beyond the automated total mismatch warrants holding payment."
}
```

## VP draft 1

```json
{
  "action": "reject",
  "reasons": [
    {
      "text": "F1 is a reject-severity total mismatch: line amount $2,500 plus shipping $75 equals $2,575, but the invoice total is $2,475 (short $100). Tax is blank, so the gap is an unclassified error, not a documented discount. A reject finding blocks payment.",
      "finding_ids": [
        "F1"
      ]
    }
  ],
  "addressed_findings": [
    "F1"
  ],
  "summary": "Reject INV-3009 from TechParts International. The $2,475 total does not match lines plus shipping of $2,575 (F1), so the invoice cannot be paid."
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
  "reasoning": "INV-3009 is rejected under F1 because the stated total of $2,475.00 does not equal line amounts plus shipping. Lines are $2,500.00, tax is blank, and shipping is $75.00, which sums to $2,575.00, a $100.00 shortfall with no documented discount. A corrected invoice can be resubmitted, so the disposition is return_to_vendor.",
  "vendor_reply": "Hello TechParts International billing team, we cannot process invoice INV-3009 because the total does not match the line and shipping amounts. Widget A is $2,500.00 (10 × $250.00), shipping is $75.00, and tax is blank, which adds to $2,575.00, but the invoice total is $2,475.00. Please resubmit a corrected invoice whose total equals the line amounts plus any tax and shipping, with each amount shown clearly."
}
```
