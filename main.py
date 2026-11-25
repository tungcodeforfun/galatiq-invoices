"""Command line: process one invoice, a folder, the scorecard, or reset the database."""

from __future__ import annotations

import argparse
import contextlib
import json
import subprocess
import sys
from pathlib import Path

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from invoice_agents import fallback
from invoice_agents.db import DEFAULT_DB, Store
from invoice_agents.graph import stream
from invoice_agents.nodes import Deps, State
from invoice_agents.observability import cost_label, short_labels, usage_cell, usage_summary

SUFFIXES = {".txt", ".json", ".csv", ".xml", ".pdf", ".md", ".eml"}
STYLE = {"PAID": "green", "REJECTED": "red", "PAYMENT_FAILED": "yellow"}


def step_line(node: str, s: State) -> str | None:
    """One progress line per graph step, or None for steps that show nothing new."""
    inv = s.get("invoice")
    match node:
        case "intake" if inv:
            return (f"Intake      {inv.invoice_number or '?'} · {inv.vendor or 'no vendor'} · "
                    f"{len(inv.line_items)} lines · {inv.total if inv.total is not None else '?'} {inv.currency or ''}")
        case "intake":
            return "Intake      could not read the document"
        case "check":
            errors = s.get("extraction_errors")
            return f"Check       {len(errors)} value(s) do not trace to the document" if errors else \
                "Check       every value traces to the document"
        case "validator":
            return f"Validator   {len(s.get('tool_calls', []))} tool calls so far"
        case "coverage":
            forced = s.get("coverage_forced")
            return f"Coverage    ran {len(forced)} skipped check(s) in code" if forced else None
        case "risk" if s.get("risk"):
            memo = s["risk"]
            return f"Risk        {memo.level} · {len(memo.signals)} signal(s)"
        case "approver":
            d = s["drafts"][-1]
            return f"VP          draft {len(s['drafts'])}: {d.action}"
        case "critic":
            c = s["critiques"][-1]
            return f"Critic      {c.verdict}" + (f" · {len(c.objections)} objection(s)" if c.objections else "")
        case "gate":
            g = s["gate"]
            return "Gate        pass" if g.approved else f"Gate        blocked: {', '.join(g.blocked_by)}"
        case "payment" if s.get("payment"):
            p = s["payment"]
            return f"Payment     {p.status} · {p.amount:,.2f} · attempt {p.attempts}"
        case "resolution" if s.get("resolution"):
            return f"Resolution  {s['resolution'].disposition}"
    return None


def run_one(path: Path, db: Path, console: Console, verbose: bool = True) -> tuple[State, Deps]:
    """Process one invoice, printing each agent step as it finishes."""
    deps = Deps.create(path, db)
    if verbose:
        console.print(f"[bold]{path}[/]  [dim]{deps.llm.model} · {deps.llm.mode} · run {deps.log.run_id}[/]")
    state: State = {}
    for node, state in stream(path, deps):
        line = step_line(node, state)
        if verbose and line:
            console.print(f"  [cyan]✓[/] {line}")
    if verbose:
        show_result(state, deps, console)
    return state, deps


def show_result(s: State, deps: Deps, console: Console) -> None:
    """Findings table, outcome panel, vendor reply and log locations."""
    if s.get("findings"):
        table = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
        for col in ("ID", "Code", "Severity", "Finding"):
            table.add_column(col)
        for f in s["findings"]:
            table.add_row(f.id, f.code, f.severity.value, f.message)
        console.print(table)
    out = s["outcome"]
    title = out.status + (f" · {out.disposition}" if out.disposition else "")
    console.print(Panel(out.summary, title=title, title_align="left", border_style=STYLE[out.status]))
    reply = s["resolution"].vendor_reply if s.get("resolution") else None
    if reply:
        console.print(Panel(reply, title="Draft reply to vendor", title_align="left", border_style="dim"))
    if s.get("degraded"):
        console.print("[yellow]" + fallback.notice(s["degraded"], deps.llm.mode != "replay") + "[/]")
    t = deps.log.totals()
    console.print(f"[dim]{t['seconds']}s · {t['llm_calls']} model calls ({', '.join(t['tiers']) or 'none'}) · "
                  f"{t['tool_calls']} tool calls · {t['tokens']} tokens · {cost_label(t)} · "
                  f"log {deps.log.dir}/events.jsonl · {deps.log.dir}/report.md[/]")


def invoice_files(folder: Path) -> list[Path]:
    """Invoice files in a folder, in name order."""
    return sorted(p for p in folder.iterdir() if p.suffix.lower() in SUFFIXES)


def run_batch(paths: list[Path], db: Path, console: Console) -> list[tuple[Path, State]]:
    """Process several invoices in order and print a summary table that fits 80 columns."""
    results = []
    totals = []
    labels = short_labels([p.name for p in paths])
    table = Table(header_style="bold", box=box.SIMPLE_HEAD, show_edge=False, pad_edge=False)
    table.add_column("File", no_wrap=True)
    table.add_column("Outcome")
    table.add_column("Amount", justify="right")
    table.add_column("Findings")
    table.add_column("Time · calls · cost", min_width=len("$0.0000"))
    with console.status("") as status:
        for path in paths:
            status.update(f"Processing {path.name}")
            state, deps = run_one(path, db, console, verbose=False)
            out, t = state["outcome"], deps.log.totals()
            results.append((path, state))
            totals.append(t)
            outcome = f"[{STYLE[out.status]}]{out.status}[/]" + (f" · {out.disposition.replace('_', ' ')}"
                                                                 if out.disposition else "")
            table.add_row(labels[path.name], outcome, f"{out.amount:,.2f}" if out.amount else "",
                          ", ".join(f.code for f in state["findings"]), usage_cell(t))
    table.columns[3].min_width = max((len(f.code) for _, s in results for f in s["findings"]), default=0)
    console.print(table)
    paid = [s["outcome"].amount or 0 for _, s in results if s["outcome"].status == "PAID"]
    console.print(f"{len(paid)} of {len(results)} paid · {sum(paid):,.2f} paid")
    console.print("Calls = model calls / tool calls. " + usage_summary(totals))
    return results


def main(argv: list[str] | None = None) -> int:
    """Parse the command line and run the chosen command."""
    parser = argparse.ArgumentParser(description="Acme Corp invoice processing agents")
    parser.add_argument("command", nargs="?", choices=["run", "batch", "eval", "reset", "demo"], default="run")
    parser.add_argument("target", nargs="?", help="invoice file for run, folder for batch")
    parser.add_argument("--invoice_path", help="invoice file to process")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="SQLite database file")
    parser.add_argument("--json", action="store_true", help="print the outcome as JSON")
    parser.add_argument("--port", type=int, default=8501, help="dashboard port for demo")
    parser.add_argument("--set", default="samples", choices=["samples", "heldout"],
                        help="answer key for eval: the samples and extras, or the held-out set")
    args = parser.parse_args(argv)
    console = Console()

    if args.command == "reset":
        Store(args.db).reset()
        console.print(f"Reset {args.db}: inventory reseeded, ledger and payments empty")
        return 0
    if args.command == "eval":
        from evals.scorecard import run_scorecard

        return run_scorecard(console, args.set)
    if args.command == "batch":
        run_batch(invoice_files(Path(args.target or "data/invoices")), args.db, console)
        return 0
    if args.command == "demo":
        Store(args.db).reset()
        run_batch(invoice_files(Path("data/invoices")) + invoice_files(Path("data/invoices_extra")), args.db, console)
        return subprocess.call([sys.executable, "-m", "streamlit", "run", "ui/app.py", "--server.port", str(args.port)])

    target = args.invoice_path or args.target
    if not target:
        parser.error("give an invoice: python main.py --invoice_path=data/invoices/invoice_1001.txt")
    path = Path(target)
    if not path.is_file():
        parser.error(f"no such file: {path}")
    # mock_payment prints to stdout; keep stdout clean for the JSON document.
    with contextlib.redirect_stdout(sys.stderr) if args.json else contextlib.nullcontext():
        state, deps = run_one(path, args.db, console, verbose=not args.json)
    if args.json:
        print(json.dumps({"file": str(path), **state["outcome"].model_dump(), "usage": deps.log.totals(),
                          "findings": [f.model_dump(mode="json") for f in state["findings"]]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
