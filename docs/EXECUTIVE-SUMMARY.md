# Executive summary

## The problem

Acme processes vendor invoices by hand. The case puts the cost at about **$2M a year**, with a **30% error rate** and **five-day delays**: a person reads each invoice, checks it against inventory, chases a VP for approval and keys the payment.

## What the system does

Invoices go in as files: text, PDF, spreadsheet exports, JSON, XML or email. Each comes out **paid** or **rejected with a reason**, in about a minute and a half. Clean invoices pay with nobody touching them. A rejected invoice carries its evidence and, when the vendor can fix it, a drafted email that names exactly what to correct.

Grok does the reading and the judgment: one agent checks the invoice against stock, prices and past invoices, one looks for fraud, a VP agent decides and a critic challenges the decision. Plain code does every sum and lookup and has the last word on money: no agent can pay an invoice that policy says to stop, and nothing is ever paid twice.

## Measured results

From the final run on 2026-11-25 against `grok-4.7`, one invoice at a time.

| | Galatiq's samples + 4 of mine | Held-out set |
|---|---|---|
| Invoices | 24 | 20, written after the build, answers fixed before the first run |
| Matches the answer key | **24/24** | **20/20** |
| Paid straight through | 8 (33%), $48,300 | 9 (45%), $35,745 |
| Stopped | 16, $210,611 plus one €4,125 invoice | 11, $26,470 |
| Time per invoice | 82 s average (33–203 s) | 53 s average (29–79 s) |
| Grok cost per invoice | $0.022 | $0.017 |

Every invoice the answer key says to pay was paid; every one it says to stop was stopped. The stopped ones include stock overruns, unknown items, totals that don't add up (both too high and too low), a euro invoice, corrupt data, the same bill sent twice under different numbers or formats, a revised invoice after the original was paid, a missing vendor, a negative quantity, a bank-details change and four attempts to instruct the system through the invoice text.

## The trade-off

This design spends more model calls than it has to: about **9 per invoice**, where a rules-first design would call Grok once or twice (to read the invoice, perhaps to draft the email) and decide the rest in code. That is why an invoice takes over a minute. What the extra calls buy is judgment on things no rule anticipated: a bank-change request in an email, instructions planted in the notes, a "rush order" label that explains a higher price. Each decision also comes with reasons a finance manager can check. The cost is small: at the measured $0.022 per invoice, **if** Acme handles about 50,000 invoices a year (my assumption from $2M at roughly $40 of staff time each; the case gives no volume), Grok would cost about **$1,100 a year**. That is the one projection here. If speed mattered more than depth, the first change would be to skip the critic on small invoices with nothing wrong.

## 30-day rollout

1. **Week 1:** connect the accounts-payable mailbox. Shadow mode: every decision is logged beside the clerk's, nothing is paid.
2. **Week 2:** replace the stock check with a match against purchase orders and goods receipts in the ERP; take the vendor list and bank details from the ERP.
3. **Week 3:** send rejections to the AP queue with the drafted email, and count how often a clerk sends it unchanged.
4. **Week 4:** let the system pay the straight-through class under a dollar limit, and rerun both scorecards on every prompt or policy change.

- **Well-written fraud.** A clumsy fake gets caught; a careful one with no unusual wording may get further. Instruction-like text always stops payment, by code; a bank-details change is caught by the risk analyst, which is a judgment, not a rule.

- **Answers vary from run to run.** Grok can decide differently on a second run. The two scorecards catch drift, and policy code, not the model, decides what gets paid.
- **Well-written fraud.** A clumsy fake gets caught; a careful one with no unusual wording may get further. Bank-detail changes and instruction-like text always stop payment.
- **Stand-ins.** Stock stands in for a three-way match, and the vendor list was seeded from the sample invoices. Week 2 replaces both.
- **Payments that fail mid-call.** They stay pending and block a second attempt until someone checks with the bank; nothing reconciles them automatically yet.
