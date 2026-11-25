# invoice_2003_bank_change.eml: REJECTED (void)

INV-2003 is voided under F1, a reject-severity fraud finding: the invoice asks AP to remit to new First Coastal Bank details (routing 021000089, account 4481 2290 7731) and arrived from a sender domain not on the vendor master. Policy requires void for fraud signals, so this invoice must not be paid or resubmitted. Bank details must not be updated from this document; payment remains blocked.

Run `20261125-040041-invoice_2003_bank_change-1e52` · seconds 80.8 · llm_calls 9 · tool_calls 10 · tiers ['live'] · tokens 24446 · cost_usd 0.023

## Extracted invoice

| field | value |
|---|---|
| invoice_number | INV-2003 |
| vendor | Precision Parts Ltd. |
| invoice_date | 2026-02-04 |
| due_date | 2026-03-06 |
| due_date_as_written | 2026-03-06 |
| currency | USD |
| subtotal | None |
| tax | None |
| shipping | None |
| total | 3500.0 |
| payment_terms | None |
| notes | Hello Accounts Payable,  Please note our bank details have changed. Kindly remit payment for the invoice below to our new account:    Bank: First Coastal Bank   Routing: 021000089   Account: 4481 2290 7731  Please confirm once your records are updated.  Billing Team Precision Parts Ltd. |
| revision | None |

| # | description | qty | unit price | amount | note |
|---|---|---|---|---|---|
| 1 | WidgetB | 4.0 | 500.0 | None |  |
| 2 | GadgetX | 2.0 | 750.0 | None |  |

## Findings

| id | code | severity | message | source |
|---|---|---|---|---|
| F1 | FRAUD_SIGNALS | reject | Risk analyst: Do not pay. This known vendor's invoice is paired with a request to use new bank details and arrives from a sender domain the vendor master does not recognize. | risk |

## Tool calls

| by | tool | args | result |
|---|---|---|---|
| validator | resolve_item | {"line": 1} | {"line": 1, "description": "WidgetB", "item": "WidgetB", "match": "exact"} |
| validator | resolve_item | {"line": 2} | {"line": 2, "description": "GadgetX", "item": "GadgetX", "match": "exact"} |
| validator | check_totals | {} | {"lines_sum": 3500.0, "expected_total": 3500.0, "stated_total": 3500.0, "problems": [], "ok": true} |
| validator | check_duplicate | {} | {"result": "no_match"} |
| validator | get_vendor | {"name": "Precision Parts Ltd."} | {"known": true, "name": "Precision Parts Ltd.", "aliases": [], "first_seen": "2024-01-08", "earlier_invoices": [{"number": "INV-1004", "total": 1890.0, "status" |
| validator | check_stock | {"item": "WidgetB"} | {"item": "WidgetB", "lines": [1], "requested": 4.0, "in_stock": 10, "ok": true} |
| validator | check_stock | {"item": "GadgetX"} | {"item": "GadgetX", "lines": [2], "requested": 2.0, "in_stock": 5, "ok": true} |
| validator | check_price | {"line": 1} | {"line": 1, "item": "WidgetB", "invoiced": 500.0, "catalog": 500.0, "variance_pct": 0.0, "within_tolerance": true} |
| validator | check_price | {"line": 2} | {"line": 2, "item": "GadgetX", "invoiced": 750.0, "catalog": 750.0, "variance_pct": 0.0, "within_tolerance": true} |
| risk | get_vendor | {"name": "Precision Parts Ltd."} | {"known": true, "name": "Precision Parts Ltd.", "aliases": [], "first_seen": "2024-01-08", "earlier_invoices": [{"number": "INV-1004", "total": 1890.0, "status" |

## Validator notes

```json
{
  "checks_run": [
    "resolve_item(1)",
    "resolve_item(2)",
    "check_totals",
    "check_duplicate",
    "get_vendor(Precision Parts Ltd.)",
    "check_stock(WidgetB)",
    "check_stock(GadgetX)",
    "check_price(1)",
    "check_price(2)"
  ],
  "concerns": [
    "Invoice notes instruct AP to remit to a new First Coastal Bank account (routing 021000089, account 4481 2290 7731). Do not update payee details from the invoice; confirm any bank change with the vendor through a known channel before payment.",
    "Vendor history lists INV-1004 twice with different totals and outcomes (PAID 1890.00 and REJECTED 5940.00, return_to_vendor). This invoice was not flagged as a duplicate, but the conflicting prior number is worth a look."
  ],
  "summary": "INV-2003 from Precision Parts Ltd. matched WidgetB and GadgetX exactly; stock, unit prices, totals, and duplicate checks were clean. The only material issue is the unsolicited bank-detail change in the notes, plus a conflicting prior INV-1004 on the vendor record."
}
```

## Risk memo

```json
{
  "level": "high",
  "signals": [
    {
      "kind": "payment_redirect",
      "quote": "Please note our bank details have changed. Kindly remit payment for the invoice below to our new account:",
      "why": "The document asks AP to send this payment to a newly stated bank account, which is a classic payment-diversion request."
    },
    {
      "kind": "payment_redirect",
      "quote": "Bank: First Coastal Bank\n  Routing: 021000089\n  Account: 4481 2290 7731",
      "why": "Specific new routing and account numbers are given as the remit destination and are not explained by the vendor master."
    },
    {
      "kind": "vendor_change",
      "quote": "From: billing@precision-parts-payments.com",
      "why": "The sender address does not match Precision Parts Ltd., and the vendor master lists no alias that would explain that identity."
    }
  ],
  "summary": "Do not pay. This known vendor's invoice is paired with a request to use new bank details and arrives from a sender domain the vendor master does not recognize."
}
```

## VP draft 1

```json
{
  "action": "reject",
  "reasons": [
    {
      "text": "F1 is a reject-severity fraud finding: the invoice asks AP to remit to new First Coastal Bank details (routing 021000089, account 4481 2290 7731) and the sender domain is not on the vendor master. Payment is blocked.",
      "finding_ids": [
        "F1"
      ]
    },
    {
      "text": "The risk memo is high, driven by payment-redirect and unrecognized sender (billing@precision-parts-payments.com). A high-risk memo requires rejection; bank changes must be confirmed on a known channel, not taken from the invoice.",
      "finding_ids": [
        "F1"
      ]
    }
  ],
  "addressed_findings": [
    "F1"
  ],
  "summary": "Reject INV-2003 ($3,500). A reject-severity fraud finding and a high-risk payment-diversion memo block payment; do not update payee bank details from this invoice."
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
  "reasoning": "INV-2003 is voided under F1, a reject-severity fraud finding: the invoice asks AP to remit to new First Coastal Bank details (routing 021000089, account 4481 2290 7731) and arrived from a sender domain not on the vendor master. Policy requires void for fraud signals, so this invoice must not be paid or resubmitted. Bank details must not be updated from this document; payment remains blocked.",
  "vendor_reply": null
}
```
