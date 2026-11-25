"""Per-run structured log (runs/<run_id>/events.jsonl) and a readable report.md with the full agent transcript."""

from __future__ import annotations

import json
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

RUNS_DIR = Path("runs")
TICKS_PER_USD = 10**10


class RunLog:
    """Append-only event log for one invoice run."""

    def __init__(self, invoice_path: Path, root: Path = RUNS_DIR):
        stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        self.run_id = f"{stamp}-{invoice_path.stem}-{uuid.uuid4().hex[:4]}"
        self.dir = root / self.run_id
        self.dir.mkdir(parents=True, exist_ok=True)
        self.events: list[dict[str, Any]] = []
        self._started = time.perf_counter()

    def emit(self, kind: str, **data: Any) -> None:
        """Record one event with a wall-clock timestamp and milliseconds since the run started."""
        event = {
            "ts": datetime.now(UTC).isoformat(timespec="milliseconds"),
            "t_ms": round((time.perf_counter() - self._started) * 1000),
            "run_id": self.run_id,
            "kind": kind,
            **data,
        }
        self.events.append(event)
        with (self.dir / "events.jsonl").open("a") as f:
            f.write(json.dumps(event, default=str) + "\n")

    def llm_call(self, agent: str, tier: str, key: str, latency_ms: int, usage: dict[str, Any]) -> None:
        """Log one model call: agent, live or replayed, tokens, latency, and cost as xAI billed it when recorded."""
        details = usage.get("completion_tokens_details") or {}
        self.emit(
            "llm_call",
            agent=agent,
            tier=tier,
            request=key[:12],
            latency_ms=latency_ms,
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            reasoning_tokens=details.get("reasoning_tokens"),
            cost_usd=(usage.get("cost_in_usd_ticks") or 0) / TICKS_PER_USD,
        )

    def totals(self) -> dict[str, Any]:
        """Seconds, model calls, tool calls, tokens and Grok cost for this run; replayed cost is the recorded cost."""
        calls = [e for e in self.events if e["kind"] == "llm_call"]
        return {
            "seconds": round((time.perf_counter() - self._started), 1),
            "llm_calls": len(calls),
            "tool_calls": sum(e["kind"] == "tool_call" for e in self.events),
            "tiers": sorted({c["tier"] for c in calls}),
            "tokens": sum((c["prompt_tokens"] or 0) + (c["completion_tokens"] or 0) for c in calls),
            "cost_usd": round(sum(c["cost_usd"] for c in calls), 4),
        }


def _table(rows: list[list[Any]], header: list[str]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(str(c).replace("|", "/").replace("\n", " ") for c in r) + " |" for r in rows]
    return "\n".join(lines)


def _plain(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_plain(v) for v in value]
    return value


def save_state(log: RunLog, state: dict[str, Any]) -> Path:
    """Write state.json: the final graph state, for the dashboard to show any past run."""
    plain = {k: _plain(v) for k, v in state.items()}
    path = log.dir / "state.json"
    path.write_text(json.dumps({**plain, "run_id": log.run_id, "totals": log.totals()}, indent=1, default=str))
    return path


def load_state(run_dir: Path) -> dict[str, Any] | None:
    """A past run's final state, or None if the run did not finish."""
    path = run_dir / "state.json"
    return json.loads(path.read_text()) if path.exists() else None


def write_report(log: RunLog, state: dict[str, Any]) -> Path:
    """Write report.md: outcome, extracted invoice, findings, tool calls and every agent's output."""
    out, inv = state["outcome"], state.get("invoice")
    parts = [f"# {Path(state['path']).name}: {out.status}" + (f" ({out.disposition})" if out.disposition else ""),
             "", out.summary, "", f"Run `{log.run_id}` · " + " · ".join(f"{k} {v}" for k, v in log.totals().items())]
    if state.get("degraded"):
        parts += ["", "**Degraded mode:** " + "; ".join(state["degraded"])]
    if inv:
        parts += ["", "## Extracted invoice", "", _table(
            [[k, v] for k, v in inv.model_dump(exclude={"line_items", "corrections"}).items()], ["field", "value"]),
            "", _table([[n, li.description, li.quantity, li.unit_price, li.amount, li.note or ""]
                        for n, li in enumerate(inv.line_items, 1)],
                       ["#", "description", "qty", "unit price", "amount", "note"])]
    if state.get("findings"):
        parts += ["", "## Findings", "", _table([[f.id, f.code, f.severity.value, f.message, f.source]
                                                 for f in state["findings"]],
                                                ["id", "code", "severity", "message", "source"])]
    if state.get("tool_calls"):
        parts += ["", "## Tool calls", "", _table(
            [[c["by"], c["tool"], json.dumps(c["args"]), json.dumps(c["result"])[:160]] for c in state["tool_calls"]],
            ["by", "tool", "args", "result"])]
    for title, key in (("Validator notes", "validator_notes"), ("Risk memo", "risk")):
        if state.get(key):
            parts += ["", f"## {title}", "", "```json", state[key].model_dump_json(indent=2), "```"]
    for n, draft in enumerate(state.get("drafts") or [], 1):
        parts += ["", f"## VP draft {n}", "", "```json", draft.model_dump_json(indent=2), "```"]
        critiques = state.get("critiques") or []
        if n <= len(critiques):
            parts += ["", f"## Critique {n}", "", "```json", critiques[n - 1].model_dump_json(indent=2), "```"]
    for title, key in (("Policy gate", "gate"), ("Payment", "payment"), ("Resolution", "resolution")):
        if state.get(key):
            parts += ["", f"## {title}", "", "```json", state[key].model_dump_json(indent=2), "```"]
    path = log.dir / "report.md"
    path.write_text("\n".join(parts) + "\n")
    return path
