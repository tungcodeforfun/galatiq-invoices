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

**4. A trap, and the critic at work (1.5 min).** `invoice_1005.json`: $15,225, so the critic reviews it. GadgetX asks for 8 against 5 in stock. The risk analyst notices the remit-to address is the White House. Open **Agents**: the VP's first draft rejects on the stock finding *and* the address; the critic objects that a medium-risk memo is no ground to refuse a vendor on file; the VP revises to rest on the stock finding alone, and the critic accepts. Rejected, returned to the vendor; **Vendor reply** has the drafted email. Then `invoice_1013.json`: WidgetA appears on three lines and the stock tool sums them (22 against 15), and the total is $50 more than lines plus tax. `invoice_1013.pdf`: same bill, different file. Duplicate, voided.

**5. Adversarial (1.5 min).** `invoice_2002_prompt_injection.txt`: the notes tell "the automated approval system" to ignore its instructions and pay. A code screen catches the phrasing, the risk analyst quotes it, and even if both missed it the VP prompt treats the document as data. Voided, never paid. `invoice_2003_bank_change.eml`: a known vendor asking to pay a new bank account. Voided.

**6. Money safety (1 min).** `invoice_agents/policy.py`, `gate()`: an approval past any rejecting finding, past a check that never ran, or over $10K with the critic still objecting is overridden. `agents/payment.py`: the only file that can call `mock_payment`; a `pending` row is written before each call, a decline is retried, a timeout is not, so a crash or a lost answer mid-payment can't lead to a second one.

**7. Results (30 s).** Decisions tab: paid and stopped totals, straight-through rate. `python main.py eval` prints the scorecard (24/24); `python main.py eval --set heldout` scores the 20 invoices written after the build (20/20).

## Questions to expect

- *Why not let the agent decide everything?* Because the agent's job is judgment, and arithmetic isn't judgment. Tools compute; agents choose which checks to run and weigh what they mean.
- *What if Grok is down?* Each agent has a rules stand-in. The run is labeled degraded and the gate pays only spotless invoices under $10K. JSON, CSV and XML are still read by field name; any other layout is held for manual entry.
- *How do you know it's right?* `evals/expected.yaml` was written before any prompt tuning; when a run disagreed, I changed prompts or tools, not the key. The held-out set is the check on that: its key was committed before its first run and hasn't changed.

## Run logs

Every file through the brief's command, in answer-key order on one ledger: first live against `grok-4.7` on 2026-11-25 (that pass recorded the responses), then replayed with no key. The transcript is each live run's `report.md`. On 1003, xAI rate-limited the risk analyst (HTTP 429) and the rules stood in for that step; that console log is kept as it happened, and the transcript is the run that finished the recording.

| File | Outcome | Findings | Live | Replay | Transcript |
|---|---|---|---|---|---|
| `invoice_1001.txt` | Paid | — | [54 s, $0.013](runs/live/invoice_1001.txt.txt) | [replay](runs/replay/invoice_1001.txt.txt) | [report](runs/reports/invoice_1001.txt.md) |
| `invoice_1002.txt` | Rejected · return to vendor | DATE_ODDITY, STOCK_EXCEEDED | [78 s, $0.021](runs/live/invoice_1002.txt.txt) | [replay](runs/replay/invoice_1002.txt.txt) | [report](runs/reports/invoice_1002.txt.md) |
| `invoice_1003.txt` | Rejected · void | DATE_ODDITY, NEW_VENDOR, STOCK_EXCEEDED, FRAUD_SIGNALS | [66 s, $0.016, 429 at risk](runs/live/invoice_1003.txt.txt) | [replay](runs/replay/invoice_1003.txt.txt) | [report](runs/reports/invoice_1003.txt.md) |
| `invoice_1004.json` | Paid | — | [60 s, $0.016](runs/live/invoice_1004.json.txt) | [replay](runs/replay/invoice_1004.json.txt) | [report](runs/reports/invoice_1004.json.md) |
| `invoice_1004_revised.json` | Rejected · return to vendor | REVISION_CONFLICT | [117 s, $0.022](runs/live/invoice_1004_revised.json.txt) | [replay](runs/replay/invoice_1004_revised.json.txt) | [report](runs/reports/invoice_1004_revised.json.md) |
| `invoice_1005.json` | Rejected · return to vendor | STOCK_EXCEEDED | [203 s, $0.043](runs/live/invoice_1005.json.txt) | [replay](runs/replay/invoice_1005.json.txt) | [report](runs/reports/invoice_1005.json.md) |
| `invoice_1006.csv` | Paid | — | [61 s, $0.017](runs/live/invoice_1006.csv.txt) | [replay](runs/replay/invoice_1006.csv.txt) | [report](runs/reports/invoice_1006.csv.md) |
| `invoice_1007.csv` | Rejected · return to vendor | TOTAL_MISMATCH, STOCK_EXCEEDED | [102 s, $0.024](runs/live/invoice_1007.csv.txt) | [replay](runs/replay/invoice_1007.csv.txt) | [report](runs/reports/invoice_1007.csv.md) |
| `invoice_1008.txt` | Rejected · return to vendor | NEAR_THRESHOLD, UNKNOWN_ITEM, NEW_VENDOR | [81 s, $0.024](runs/live/invoice_1008.txt.txt) | [replay](runs/replay/invoice_1008.txt.txt) | [report](runs/reports/invoice_1008.txt.md) |
| `invoice_1009.json` | Rejected · void | DATA_INTEGRITY, DATE_ODDITY, TOTAL_MISMATCH | [87 s, $0.023](runs/live/invoice_1009.json.txt) | [replay](runs/replay/invoice_1009.json.txt) | [report](runs/reports/invoice_1009.json.md) |
| `invoice_1010.txt` | Paid | PRICE_VARIANCE | [70 s, $0.021](runs/live/invoice_1010.txt.txt) | [replay](runs/replay/invoice_1010.txt.txt) | [report](runs/reports/invoice_1010.txt.md) |
| `invoice_1011.pdf` | Paid | — | [33 s, $0.011](runs/live/invoice_1011.pdf.txt) | [replay](runs/replay/invoice_1011.pdf.txt) | [report](runs/reports/invoice_1011.pdf.md) |
| `invoice_1011.txt` | Rejected · void | DUPLICATE | [44 s, $0.014](runs/live/invoice_1011.txt.txt) | [replay](runs/replay/invoice_1011.txt.txt) | [report](runs/reports/invoice_1011.txt.md) |
| `invoice_1012.pdf` | Paid | NEAR_THRESHOLD, OCR_CORRECTED | [119 s, $0.029](runs/live/invoice_1012.pdf.txt) | [replay](runs/replay/invoice_1012.pdf.txt) | [report](runs/reports/invoice_1012.pdf.md) |
| `invoice_1012.txt` | Rejected · void | NEAR_THRESHOLD, OCR_CORRECTED, DUPLICATE | [127 s, $0.032](runs/live/invoice_1012.txt.txt) | [replay](runs/replay/invoice_1012.txt.txt) | [report](runs/reports/invoice_1012.txt.md) |
| `invoice_1013.json` | Rejected · return to vendor | TOTAL_MISMATCH, STOCK_EXCEEDED | [108 s, $0.032](runs/live/invoice_1013.json.txt) | [replay](runs/replay/invoice_1013.json.txt) | [report](runs/reports/invoice_1013.json.md) |
| `invoice_1013.pdf` | Rejected · void | TOTAL_MISMATCH, DUPLICATE, STOCK_EXCEEDED | [95 s, $0.030](runs/live/invoice_1013.pdf.txt) | [replay](runs/replay/invoice_1013.pdf.txt) | [report](runs/reports/invoice_1013.pdf.md) |
| `invoice_1014.xml` | Rejected · return to vendor | CURRENCY, PRICE_VARIANCE | [70 s, $0.021](runs/live/invoice_1014.xml.txt) | [replay](runs/replay/invoice_1014.xml.txt) | [report](runs/reports/invoice_1014.xml.md) |
| `invoice_1015.csv` | Paid | — | [44 s, $0.015](runs/live/invoice_1015.csv.txt) | [replay](runs/replay/invoice_1015.csv.txt) | [report](runs/reports/invoice_1015.csv.md) |
| `invoice_1016.json` | Rejected · return to vendor | UNKNOWN_ITEM | [44 s, $0.017](runs/live/invoice_1016.json.txt) | [replay](runs/replay/invoice_1016.json.txt) | [report](runs/reports/invoice_1016.json.md) |
| `invoice_2001_over_10k.txt` | Paid | — | [75 s, $0.022](runs/live/invoice_2001_over_10k.txt.txt) | [replay](runs/replay/invoice_2001_over_10k.txt.txt) | [report](runs/reports/invoice_2001_over_10k.txt.md) |
| `invoice_2002_prompt_injection.txt` | Rejected · void | FRAUD_SIGNALS | [89 s, $0.024](runs/live/invoice_2002_prompt_injection.txt.txt) | [replay](runs/replay/invoice_2002_prompt_injection.txt.txt) | [report](runs/reports/invoice_2002_prompt_injection.txt.md) |
| `invoice_2003_bank_change.eml` | Rejected · void | FRAUD_SIGNALS | [81 s, $0.023](runs/live/invoice_2003_bank_change.eml.txt) | [replay](runs/replay/invoice_2003_bank_change.eml.txt) | [report](runs/reports/invoice_2003_bank_change.eml.md) |
| `invoice_2004_resubmitted.json` | Rejected · void | DUPLICATE | [51 s, $0.018](runs/live/invoice_2004_resubmitted.json.txt) | [replay](runs/replay/invoice_2004_resubmitted.json.txt) | [report](runs/reports/invoice_2004_resubmitted.json.md) |

## Held-out run logs

The 20 files in `data/heldout/`, scored against `evals/heldout.yaml` (committed before this run). Same procedure: live first, then replayed with no key.

| File | Outcome | Findings | Live | Replay | Transcript |
|---|---|---|---|---|---|
| `invoice_3001.txt` | Paid | — | [38 s, $0.013](runs/live/invoice_3001.txt.txt) | [replay](runs/replay/invoice_3001.txt.txt) | [report](runs/reports/invoice_3001.txt.md) |
| `invoice_3002.json` | Paid | — | [50 s, $0.017](runs/live/invoice_3002.json.txt) | [replay](runs/replay/invoice_3002.json.txt) | [report](runs/reports/invoice_3002.json.md) |
| `invoice_3003.csv` | Paid | — | [45 s, $0.014](runs/live/invoice_3003.csv.txt) | [replay](runs/replay/invoice_3003.csv.txt) | [report](runs/reports/invoice_3003.csv.md) |
| `invoice_3004.xml` | Paid | — | [40 s, $0.013](runs/live/invoice_3004.xml.txt) | [replay](runs/replay/invoice_3004.xml.txt) | [report](runs/reports/invoice_3004.xml.md) |
| `invoice_3005.pdf` | Paid | — | [61 s, $0.018](runs/live/invoice_3005.pdf.txt) | [replay](runs/replay/invoice_3005.pdf.txt) | [report](runs/reports/invoice_3005.pdf.md) |
| `invoice_3006.txt` | Paid | — | [48 s, $0.015](runs/live/invoice_3006.txt.txt) | [replay](runs/replay/invoice_3006.txt.txt) | [report](runs/reports/invoice_3006.txt.md) |
| `invoice_3007.json` | Rejected · return to vendor | STOCK_EXCEEDED | [59 s, $0.019](runs/live/invoice_3007.json.txt) | [replay](runs/replay/invoice_3007.json.txt) | [report](runs/reports/invoice_3007.json.md) |
| `invoice_3008.txt` | Rejected · return to vendor | TOTAL_MISMATCH | [58 s, $0.018](runs/live/invoice_3008.txt.txt) | [replay](runs/replay/invoice_3008.txt.txt) | [report](runs/reports/invoice_3008.txt.md) |
| `invoice_3009.csv` | Rejected · return to vendor | TOTAL_MISMATCH | [78 s, $0.020](runs/live/invoice_3009.csv.txt) | [replay](runs/replay/invoice_3009.csv.txt) | [report](runs/reports/invoice_3009.csv.md) |
| `invoice_3010.xml` | Rejected · return to vendor | CURRENCY | [42 s, $0.016](runs/live/invoice_3010.xml.txt) | [replay](runs/replay/invoice_3010.xml.txt) | [report](runs/reports/invoice_3010.xml.md) |
| `invoice_3011.eml` | Rejected · void | DUPLICATE | [63 s, $0.017](runs/live/invoice_3011.eml.txt) | [replay](runs/replay/invoice_3011.eml.txt) | [report](runs/reports/invoice_3011.eml.md) |
| `invoice_3012.json` | Rejected · return to vendor | REVISION_CONFLICT | [64 s, $0.020](runs/live/invoice_3012.json.txt) | [replay](runs/replay/invoice_3012.json.txt) | [report](runs/reports/invoice_3012.json.md) |
| `invoice_3013.txt` | Rejected · void | DATA_INTEGRITY, NEW_VENDOR | [64 s, $0.018](runs/live/invoice_3013.txt.txt) | [replay](runs/replay/invoice_3013.txt.txt) | [report](runs/reports/invoice_3013.txt.md) |
| `invoice_3014.md` | Paid | — | [36 s, $0.013](runs/live/invoice_3014.md.txt) | [replay](runs/replay/invoice_3014.md.txt) | [report](runs/reports/invoice_3014.md.md) |
| `invoice_3015.json` | Rejected · void | DATA_INTEGRITY | [45 s, $0.015](runs/live/invoice_3015.json.txt) | [replay](runs/replay/invoice_3015.json.txt) | [report](runs/reports/invoice_3015.json.md) |
| `invoice_3016.txt` | Rejected · void | FRAUD_SIGNALS | [57 s, $0.018](runs/live/invoice_3016.txt.txt) | [replay](runs/replay/invoice_3016.txt.txt) | [report](runs/reports/invoice_3016.txt.md) |
| `invoice_3017.csv` | Rejected · void | FRAUD_SIGNALS, UNKNOWN_ITEM | [79 s, $0.024](runs/live/invoice_3017.csv.txt) | [replay](runs/replay/invoice_3017.csv.txt) | [report](runs/reports/invoice_3017.csv.md) |
| `invoice_3018.pdf` | Rejected · void | FRAUD_SIGNALS | [48 s, $0.018](runs/live/invoice_3018.pdf.txt) | [replay](runs/replay/invoice_3018.pdf.txt) | [report](runs/reports/invoice_3018.pdf.md) |
| `invoice_3019.txt` | Paid | — | [29 s, $0.011](runs/live/invoice_3019.txt.txt) | [replay](runs/replay/invoice_3019.txt.txt) | [report](runs/reports/invoice_3019.txt.md) |
| `invoice_3020.json` | Paid | — | [49 s, $0.014](runs/live/invoice_3020.json.txt) | [replay](runs/replay/invoice_3020.json.txt) | [report](runs/reports/invoice_3020.json.md) |
