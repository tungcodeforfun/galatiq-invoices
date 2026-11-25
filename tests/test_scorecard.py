from __future__ import annotations

from evals.scorecard import Score, stopped_usd


def rejected(key: str, total: float, currency: str = "USD") -> Score:
    return Score(file=key, expected={}, outcome="REJECTED", disposition="void", amount=None, codes=[],
                 invoice_key=key, total=total, currency=currency, usage={}, degraded=False)


def test_usd_stopped_counts_a_resubmitted_invoice_once_and_skips_other_currencies():
    scores = [rejected("acme|1013", 22562.80), rejected("acme|1013", 22562.80), rejected("tech|1014", 4125.0, "EUR"),
              rejected("quick|1012", 9975.0)]
    assert stopped_usd(scores) == 22562.80 + 9975.0
