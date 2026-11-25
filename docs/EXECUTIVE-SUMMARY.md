# Executive summary

## The problem

Acme processes vendor invoices by hand: about **$2M a year**, a **30% error rate** and **five-day delays**, by the case's figures.

## What the system does

Invoices go in as files (text, PDF, CSV, JSON, XML, email) and come out **paid** or **rejected with a reason**. Clean invoices pay with nobody touching them; a rejection carries its evidence and, when the vendor can fix it, a drafted email.

Grok agents check stock, prices and past invoices, look for fraud, decide as a VP and challenge that decision as a critic. Plain code does every sum and lookup and has the last word on money: no agent can pay what policy stops, and nothing is paid twice.

## Measured results

Final live run, 2026-11-25, `grok-4.7`, one file at a time within each set; the two sets overlapped for about 18 minutes, which may have slowed both.

| | Galatiq's samples + 4 of mine | Held-out set |
|---|---|---|
| Invoices | 24 | 20, written after the build, answers fixed first |
| Matches the answer key | **24/24** | **20/20** |
| Paid straight through | 8, $48,300 | 9, $35,745 |
| Stopped | 16, $210,611 plus one €4,125 invoice | 11, $26,470 plus one €2,000 invoice |
| Time per invoice | 82 s average (33–203 s) | 53 s average (29–79 s) |
| Grok cost per invoice | $0.022 | $0.017 |

## The trade-off

About **9 model calls per invoice**, where a rules-first design would make one or two. That is why an invoice takes over a minute; it buys judgment on things no rule anticipated, with reasons a finance manager can check. **If** Acme handles about 50,000 invoices a year (my assumption: $2M at roughly $40 of staff time each; the case gives no volume), Grok would cost about **$1,100 a year**.

## 30-day rollout

1. **Week 1:** connect the AP mailbox in shadow mode: decisions logged beside the clerk's, nothing paid.
2. **Week 2:** replace the stock check with a purchase-order and goods-receipt match; vendors and bank details from the ERP.
3. **Week 3:** send rejections to the AP queue with the drafted email; count how often it goes out unchanged.
4. **Week 4:** pay the straight-through class under a dollar limit; rerun both scorecards on every prompt or policy change.

## Risks

- **Well-written fraud.** With a key, the risk analyst reads the whole document. In both sets every bank change and planted instruction was stopped, by that analyst or by an English keyword screen in code, but a judgment and a keyword list are not guarantees. With no model, the system can reject an invoice by rule but never pays one.
- **Answers vary between runs.** The scorecards catch drift; policy code, not the model, decides what gets paid.
- **Stand-ins.** Stock stands in for a three-way match and the vendor list was seeded from the samples. Week 2 replaces both.
- **Payments that fail mid-call** stay pending and block a retry until someone checks with the bank.
