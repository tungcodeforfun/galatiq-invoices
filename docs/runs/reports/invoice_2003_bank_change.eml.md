# invoice_2003_bank_change.eml: REJECTED (void)

INV-2003 is voided under F1, a reject-severity fraud finding: a non-matching sender redirected payment to a bank account that the vendor master does not explain. Policy requires void for fraud signals so this invoice must not be resubmitted or paid. The payment gate and the high-risk memo independently require rejection.

Run `20261125-020228-invoice_2003_bank_change-cdfb` · seconds 79.1 · llm_calls 9 · tool_calls 10 · tiers ['live'] · tokens 23476 · cost_usd 0.0192

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
| notes | Please note our bank details have changed. Kindly remit payment for the invoice below to our new account:    Bank: First Coastal Bank   Routing: 021000089   Account: 4481 2290 7731  Please confirm once your records are updated. |
| revision | None |

| # | description | qty | unit price | amount | note |
|---|---|---|---|---|---|
| 1 | WidgetB | 4.0 | 500.0 | None |  |
| 2 | GadgetX | 2.0 | 750.0 | None |  |

## Findings

| id | code | severity | message | source |
|---|---|---|---|---|
| F1 | FRAUD_SIGNALS | reject | Risk analyst: Do not pay. A non-matching sender is redirecting INV-2003 to a new bank account that the vendor master does not explain. | risk |

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
    "resolve_item(line 1)",
    "resolve_item(line 2)",
    "check_stock(WidgetB)",
    "check_stock(GadgetX)",
    "check_price(line 1)",
    "check_price(line 2)",
    "check_totals",
    "check_duplicate",
    "get_vendor(Precision Parts Ltd.)"
  ],
  "concerns": [
    "Invoice notes ask AP to ignore the usual payee and remit to a newly stated First Coastal Bank account. That bank-detail change was not verified by any tool and is a payment-diversion risk; confirm through a known vendor channel before updating records.",
    "Vendor master lists two earlier invoices both numbered INV-1004, one PAID at 1890.00 and one REJECTED at 5940.00 (return_to_vendor). This invoice is not a ledger duplicate, but that conflicting history is worth a look before approval."
  ],
  "summary": "Both lines matched the catalog (WidgetB, GadgetX). Stock, unit prices, totals, and duplicate lookup all came back clean for a known vendor. The unflagged issues are a bank-account change in the notes and two prior INV-1004 records with opposite dispositions."
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
      "why": "The message asks AP to send this payment to a newly stated bank account rather than the vendor's established remit-to."
    },
    {
      "kind": "vendor_change",
      "quote": "From: billing@precision-parts-payments.com",
      "why": "The sender domain is not Precision Parts Ltd. and is not an alias on the vendor master, so the party demanding the new account does not match the known vendor."
    }
  ],
  "summary": "Do not pay. A non-matching sender is redirecting INV-2003 to a new bank account that the vendor master does not explain."
}
```

## VP draft 1

```json
{
  "action": "reject",
  "reasons": [
    {
      "text": "F1 is a reject-severity fraud finding: a non-matching sender is redirecting INV-2003 to a new bank account not on the vendor master. The payment gate blocks this invoice, and the high-risk memo independently requires rejection.",
      "finding_ids": [
        "F1"
      ]
    }
  ],
  "addressed_findings": [
    "F1"
  ],
  "summary": "Reject INV-2003 ($3,500). A reject-severity fraud finding and a high-risk memo both flag a payment redirect from a sender that does not match Precision Parts Ltd."
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
  "disposition": "void",
  "reasoning": "INV-2003 is voided under F1, a reject-severity fraud finding: a non-matching sender redirected payment to a bank account that the vendor master does not explain. Policy requires void for fraud signals so this invoice must not be resubmitted or paid. The payment gate and the high-risk memo independently require rejection.",
  "vendor_reply": null
}
```
