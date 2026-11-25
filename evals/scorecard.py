"""Scorecard: run every invoice in the answer key against an empty ledger and compare with expected.yaml."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from rich.console import Console
from rich.table import Table

ANSWER_KEY = Path(__file__).resolve().parent / "expected.yaml"


@dataclass
class Score:
    """One invoice's result against its expectation."""

    file: str
    expected: dict[str, Any]
    outcome: str
    disposition: str | None
    amount: float | None
    codes: list[str]
    total: float | None
    usage: dict[str, Any]
    degraded: bool

    @property
    def missing(self) -> list[str]:
        """Required finding codes the run did not raise."""
        return [c for c in self.expected.get("findings", []) if c not in self.codes]

    @property
    def passed(self) -> bool:
        """Outcome, disposition, amount and required findings all match."""
        e = self.expected
        return (
            self.outcome == e["outcome"]
            and self.disposition == e.get("disposition")
            and (e.get("amount") is None or abs((self.amount or 0) - e["amount"]) < 0.01)
            and not self.missing
        )


def load_answer_key(path: Path = ANSWER_KEY) -> dict[str, dict[str, Any]]:
    """Expected outcome per file, in run order."""
    return yaml.safe_load(path.read_text())["invoices"]


def score_all(db: Path) -> list[Score]:
    """Process every file in the answer key, in order, on the given database."""
    from invoice_agents.db import Store
    from invoice_agents.graph import process
    from main import make_deps

    Store(db).reset()
    scores = []
    for file, expected in load_answer_key().items():
        deps = make_deps(Path(file), db)
        state = process(Path(file), deps)
        out, inv = state["outcome"], state.get("invoice")
        scores.append(Score(file=file, expected=expected, outcome=out.status, disposition=out.disposition,
                            amount=out.amount, codes=[f.code for f in state.get("findings", [])],
                            total=inv.total if inv else None, usage=deps.log.totals(),
                            degraded=bool(state.get("degraded"))))
    return scores


def run_scorecard(console: Console) -> int:
    """Print the scorecard; exit code 1 if any invoice misses its expectation."""
    from main import cost_label, usage_summary

    with tempfile.TemporaryDirectory() as tmp, console.status("Running the answer key"):
        scores = score_all(Path(tmp) / "eval.db")
    table = Table(header_style="bold")
    for col in ("File", "Expected", "Got", "Required findings", "Result", "Time", "Calls", "Cost"):
        table.add_column(col)
    for s in scores:
        e, u = s.expected, s.usage
        want = e["outcome"] + (f" · {e['disposition']}" if e.get("disposition") else "")
        got = s.outcome + (f" · {s.disposition}" if s.disposition else "") + (" (degraded)" if s.degraded else "")
        required = ", ".join(c if c in s.codes else f"[red]{c} missing[/]" for c in e.get("findings", []))
        table.add_row(Path(s.file).name, want.replace("_to_vendor", ""), got.replace("_to_vendor", ""), required,
                      "[green]pass[/]" if s.passed else "[red]FAIL[/]", f"{u['seconds']}s",
                      f"{u['llm_calls']}/{u['tool_calls']}", cost_label(u).replace(" recorded", ""))
    console.print(table)
    passed = sum(s.passed for s in scores)
    paid = [s for s in scores if s.outcome == "PAID"]
    stopped = sum(s.total or 0 for s in scores if s.outcome == "REJECTED" and (s.total or 0) > 0)
    console.print(
        f"[bold]{passed}/{len(scores)} match the answer key[/] · {len(paid)} paid "
        f"({sum(s.amount or 0 for s in paid):,.2f}) · {len(scores) - len(paid)} rejected ({stopped:,.2f} stopped)"
    )
    console.print("Calls = model calls / tool calls. " + usage_summary([s.usage for s in scores]))
    return 0 if passed == len(scores) else 1
