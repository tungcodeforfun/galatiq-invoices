# Demo

A 7-minute walkthrough, then the run log for every invoice.

## Setup (before the call)

```bash
pip install -r requirements.txt
python main.py reset
streamlit run ui/app.py        # leave it open on the Inbox tab
```

Live Grok is optional: `export XAI_API_KEY=...` makes every call live (about a minute per invoice). Without it the recorded responses replay instantly.

## Script

**1. The problem (30 s).** Acme pays people to read invoices, check them against inventory, chase a VP for approval and key the payment. 30% errors, five days. The goal is straight-through processing for clean invoices and a ready-made answer for the rest.

**2. The brief's command (1 min).** In a terminal:

```bash
python main.py --invoice_path=data/invoices/invoice_1001.txt
```

Point at each line as it prints: intake extracted the invoice, the extraction check confirmed every value appears in the document, the validator called nine tools, risk is low, the VP approved, the gate passed, payment went through once. Then `runs/<id>/report.md`: the full transcript.

**3. A messy one that should still pay (1.5 min).** Dashboard, Inbox, `invoice_1012.pdf`, Process. The strip of agents fills in. Open **Document**: the scan says `2O26` and `$3,500.O0`; intake read them as 2026 and 3,500.00 and logged both corrections. Findings: OCR corrected, near the $10K line (info only). The critic reviewed it because findings exist. Paid.

**4. A trap (1.5 min).** `invoice_1013.json`. Eight lines, WidgetA appears three times: the stock tool sums them (22 against 15 in stock), and the totals tool finds the total is $50 more than lines plus tax. Open **Agents**: the VP's draft, the critic's objections, the revision. Rejected, returned to the vendor; **Vendor reply** has the drafted email. Then `invoice_1013.pdf`: same bill, different file. Duplicate, voided.

**5. Adversarial (1.5 min).** `invoice_2002_prompt_injection.txt`: the notes tell "the automated approval system" to ignore its instructions and pay. A code screen catches the phrasing, the risk analyst quotes it, and even if both missed it the VP prompt treats the document as data. Voided, never paid. `invoice_2003_bank_change.eml`: a known vendor asking to pay a new bank account. Voided.

**6. Money safety (1 min).** `invoice_agents/policy.py`, `gate()`: an approval past any rejecting finding, past a check that never ran, or over $10K with the critic still objecting is overridden. `agents/payment.py`: the only file that can call `mock_payment`; a `pending` row is written before each call, a decline is retried, a timeout is not, so a crash or a lost answer mid-payment can't lead to a second one.

**7. Results (30 s).** Decisions tab: paid and stopped totals, straight-through rate. `python main.py eval` prints the scorecard.

## Questions to expect

- *Why not let the agent decide everything?* Because the agent's job is judgment, and arithmetic isn't judgment. Tools compute; agents choose which checks to run and weigh what they mean.
- *What if Grok is down?* Each agent has a rules stand-in. The run is labeled degraded and the gate pays only spotless invoices under $10K.
- *How do you know it's right?* `evals/expected.yaml` was written before any prompt tuning; when a run disagreed, I changed prompts or tools, not the key.

## Run logs

Every file through the brief's command, in answer-key order on one ledger: first live against `grok-4.7` on 2026-11-25 (that pass recorded the responses), then replayed with no key. The transcript is each live run's `report.md`.

| File | Outcome | Findings | Live | Replay | Transcript |
|---|---|---|---|---|---|
| `invoice_1001.txt` | Paid | — | [43 s, $0.014](runs/live/invoice_1001.txt.txt) | [replay](runs/replay/invoice_1001.txt.txt) | [report](runs/reports/invoice_1001.txt.md) |
| `invoice_1002.txt` | Rejected · return to vendor | DATE_ODDITY, STOCK_EXCEEDED | [75 s, $0.020](runs/live/invoice_1002.txt.txt) | [replay](runs/replay/invoice_1002.txt.txt) | [report](runs/reports/invoice_1002.txt.md) |
| `invoice_1003.txt` | Rejected · void | DATE_ODDITY, NEW_VENDOR, STOCK_EXCEEDED, FRAUD_SIGNALS | [89 s, $0.024](runs/live/invoice_1003.txt.txt) | [replay](runs/replay/invoice_1003.txt.txt) | [report](runs/reports/invoice_1003.txt.md) |
| `invoice_1004.json` | Paid | — | [53 s, $0.016](runs/live/invoice_1004.json.txt) | [replay](runs/replay/invoice_1004.json.txt) | [report](runs/reports/invoice_1004.json.md) |
| `invoice_1004_revised.json` | Rejected · return to vendor | REVISION_CONFLICT | [59 s, $0.020](runs/live/invoice_1004_revised.json.txt) | [replay](runs/replay/invoice_1004_revised.json.txt) | [report](runs/reports/invoice_1004_revised.json.md) |
| `invoice_1005.json` | Rejected · return to vendor | STOCK_EXCEEDED | [109 s, $0.028](runs/live/invoice_1005.json.txt) | [replay](runs/replay/invoice_1005.json.txt) | [report](runs/reports/invoice_1005.json.md) |
| `invoice_1006.csv` | Paid | — | [48 s, $0.015](runs/live/invoice_1006.csv.txt) | [replay](runs/replay/invoice_1006.csv.txt) | [report](runs/reports/invoice_1006.csv.md) |
| `invoice_1007.csv` | Rejected · return to vendor | TOTAL_MISMATCH, STOCK_EXCEEDED | [78 s, $0.023](runs/live/invoice_1007.csv.txt) | [replay](runs/replay/invoice_1007.csv.txt) | [report](runs/reports/invoice_1007.csv.md) |
| `invoice_1008.txt` | Rejected · return to vendor | NEAR_THRESHOLD, UNKNOWN_ITEM, NEW_VENDOR | [82 s, $0.023](runs/live/invoice_1008.txt.txt) | [replay](runs/replay/invoice_1008.txt.txt) | [report](runs/reports/invoice_1008.txt.md) |
| `invoice_1009.json` | Rejected · void | DATA_INTEGRITY, DATE_ODDITY, TOTAL_MISMATCH | [101 s, $0.026](runs/live/invoice_1009.json.txt) | [replay](runs/replay/invoice_1009.json.txt) | [report](runs/reports/invoice_1009.json.md) |
| `invoice_1010.txt` | Paid | PRICE_VARIANCE | [60 s, $0.018](runs/live/invoice_1010.txt.txt) | [replay](runs/replay/invoice_1010.txt.txt) | [report](runs/reports/invoice_1010.txt.md) |
| `invoice_1011.pdf` | Paid | — | [29 s, $0.012](runs/live/invoice_1011.pdf.txt) | [replay](runs/replay/invoice_1011.pdf.txt) | [report](runs/reports/invoice_1011.pdf.md) |
| `invoice_1011.txt` | Rejected · void | DUPLICATE | [44 s, $0.015](runs/live/invoice_1011.txt.txt) | [replay](runs/replay/invoice_1011.txt.txt) | [report](runs/reports/invoice_1011.txt.md) |
| `invoice_1012.pdf` | Paid | NEAR_THRESHOLD, OCR_CORRECTED | [85 s, $0.022](runs/live/invoice_1012.pdf.txt) | [replay](runs/replay/invoice_1012.pdf.txt) | [report](runs/reports/invoice_1012.pdf.md) |
| `invoice_1012.txt` | Rejected · void | NEAR_THRESHOLD, OCR_CORRECTED, DUPLICATE | [114 s, $0.029](runs/live/invoice_1012.txt.txt) | [replay](runs/replay/invoice_1012.txt.txt) | [report](runs/reports/invoice_1012.txt.md) |
| `invoice_1013.json` | Rejected · return to vendor | TOTAL_MISMATCH, STOCK_EXCEEDED | [88 s, $0.026](runs/live/invoice_1013.json.txt) | [replay](runs/replay/invoice_1013.json.txt) | [report](runs/reports/invoice_1013.json.md) |
| `invoice_1013.pdf` | Rejected · void | TOTAL_MISMATCH, DUPLICATE, STOCK_EXCEEDED | [102 s, $0.027](runs/live/invoice_1013.pdf.txt) | [replay](runs/replay/invoice_1013.pdf.txt) | [report](runs/reports/invoice_1013.pdf.md) |
| `invoice_1014.xml` | Rejected · return to vendor | CURRENCY, PRICE_VARIANCE | [83 s, $0.020](runs/live/invoice_1014.xml.txt) | [replay](runs/replay/invoice_1014.xml.txt) | [report](runs/reports/invoice_1014.xml.md) |
| `invoice_1015.csv` | Paid | — | [48 s, $0.017](runs/live/invoice_1015.csv.txt) | [replay](runs/replay/invoice_1015.csv.txt) | [report](runs/reports/invoice_1015.csv.md) |
| `invoice_1016.json` | Rejected · return to vendor | UNKNOWN_ITEM | [60 s, $0.018](runs/live/invoice_1016.json.txt) | [replay](runs/replay/invoice_1016.json.txt) | [report](runs/reports/invoice_1016.json.md) |
| `invoice_2001_over_10k.txt` | Paid | — | [80 s, $0.019](runs/live/invoice_2001_over_10k.txt.txt) | [replay](runs/replay/invoice_2001_over_10k.txt.txt) | [report](runs/reports/invoice_2001_over_10k.txt.md) |
| `invoice_2002_prompt_injection.txt` | Rejected · void | FRAUD_SIGNALS | [68 s, $0.018](runs/live/invoice_2002_prompt_injection.txt.txt) | [replay](runs/replay/invoice_2002_prompt_injection.txt.txt) | [report](runs/reports/invoice_2002_prompt_injection.txt.md) |
| `invoice_2003_bank_change.eml` | Rejected · void | FRAUD_SIGNALS | [79 s, $0.019](runs/live/invoice_2003_bank_change.eml.txt) | [replay](runs/replay/invoice_2003_bank_change.eml.txt) | [report](runs/reports/invoice_2003_bank_change.eml.md) |
| `invoice_2004_resubmitted.json` | Rejected · void | DUPLICATE | [54 s, $0.018](runs/live/invoice_2004_resubmitted.json.txt) | [replay](runs/replay/invoice_2004_resubmitted.json.txt) | [report](runs/reports/invoice_2004_resubmitted.json.md) |
