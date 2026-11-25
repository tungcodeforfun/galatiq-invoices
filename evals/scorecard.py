"""Scorecard: run every invoice in an answer key against an empty ledger and compare with the expected outcome."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from rich import box
from rich.console import Console
from rich.table import Table

EVALS = Path(__file__).resolve().parent
ANSWER_KEYS = {"samples": EVALS / "expected.yaml", "heldout": EVALS / "heldout.yaml"}


@dataclass
class Score:
    """One invoice's result against its expectation."""

    file: str
    expected: dict[str, Any]
    outcome: str
    disposition: str | None
    amount: float | None
    codes: list[str]
    invoice_key: str
    total: float | None
    currency: str | None
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


def load_answer_key(path: Path = ANSWER_KEYS["samples"]) -> dict[str, dict[str, Any]]:
    """Expected outcome per file, in run order."""
    return yaml.safe_load(path.read_text())["invoices"]


def score_all(db: Path, key: Path = ANSWER_KEYS["samples"]) -> list[Score]:
    """Process every file in the answer key, in order, on the given database."""
    from invoice_agents.db import Store
    from invoice_agents.graph import process
    from invoice_agents.matching import invoice_key
    from invoice_agents.nodes import Deps

    Store(db).reset()
    scores = []
    for file, expected in load_answer_key(key).items():
        deps = Deps.create(Path(file), db)
        state = process(Path(file), deps)
        out, inv = state["outcome"], state.get("invoice")
        scores.append(Score(file=file, expected=expected, outcome=out.status, disposition=out.disposition,
                            amount=out.amount, codes=[f.code for f in state.get("findings", [])],
                            invoice_key=invoice_key(inv.vendor, inv.invoice_number) if inv else file,
                            total=inv.total if inv else None, currency=inv.currency if inv else None,
                            usage=deps.log.totals(), degraded=bool(state.get("degraded"))))
    return scores


def stopped_usd(scores: list[Score]) -> float:
    """USD on rejected invoices, each invoice number counted once however often it was resubmitted."""
    rejected = {s.invoice_key: s.total or 0 for s in scores
                if s.outcome == "REJECTED" and (s.total or 0) > 0 and (s.currency or "USD") == "USD"}
    return sum(rejected.values())


def run_scorecard(console: Console, answer_key: str = "samples") -> int:
    """Print the scorecard; exit code 1 if any invoice misses its expectation."""
    from invoice_agents.observability import short_labels, usage_cell, usage_summary

    with tempfile.TemporaryDirectory() as tmp, console.status("Running the answer key"):
        scores = score_all(Path(tmp) / "eval.db", ANSWER_KEYS[answer_key])
    labels = short_labels([Path(s.file).name for s in scores])
    table = Table(header_style="bold", box=box.SIMPLE_HEAD, show_edge=False, pad_edge=False)
    table.add_column("File", no_wrap=True)
    for col in ("Outcome", "Required findings", "Result"):
        table.add_column(col)
    table.add_column("Time · calls · cost", min_width=len("$0.0000"))
    for s in scores:
        e = s.expected
        want = e["outcome"] + (f" · {e['disposition']}" if e.get("disposition") else "")
        got = s.outcome + (f" · {s.disposition}" if s.disposition else "") + (" (degraded)" if s.degraded else "")
        if not got.startswith(want):
            got += f" [red](expected {want})[/]"
        required = ", ".join(c if c in s.codes else f"[red]{c} missing[/]" for c in e.get("findings", []))
        table.add_row(labels[Path(s.file).name], got.replace("_", " "), required,
                      "[green]pass[/]" if s.passed else "[red]FAIL[/]", usage_cell(s.usage))
    table.columns[2].min_width = max((len(c) for s in scores for c in s.expected.get("findings", [])), default=0)
    console.print(table)
    passed = sum(s.passed for s in scores)
    paid = [s for s in scores if s.outcome == "PAID"]
    console.print(
        f"[bold]{passed}/{len(scores)} match the answer key[/] · {len(paid)} paid "
        f"({sum(s.amount or 0 for s in paid):,.2f}) · {len(scores) - len(paid)} rejected "
        f"({stopped_usd(scores):,.2f} USD stopped)"
    )
    console.print("Calls = model calls / tool calls. " + usage_summary([s.usage for s in scores]))
    return 0 if passed == len(scores) else 1
