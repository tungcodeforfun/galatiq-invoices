"""The graph's nodes and routing rules: each node runs one agent or guard and returns its change to the state."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypedDict

from langchain_core.runnables import RunnableConfig

from invoice_agents.agents import approver, critic, intake, payment, resolution, risk, validator
from invoice_agents.db import Store
from invoice_agents.llm import LLM
from invoice_agents.loaders import UnreadableDocument, file_digest, read_document
from invoice_agents.matching import content_hash, number_key, text_key
from invoice_agents.observability import RunLog, save_state, write_report
from invoice_agents.policy import NO_MODEL, GateResult, Policy, gate, load_policy, required_disposition
from invoice_agents.rules import extraction_errors, invoice_findings
from invoice_agents.schema import Critique, Decision, Finding, Invoice, Outcome, Payment, Resolution, RiskMemo, Severity
from invoice_agents.tools import ToolBox


class State(TypedDict, total=False):
    """Everything known about one invoice as it moves through the graph."""

    path: str
    source: str
    invoice: Invoice | None
    extraction_errors: list[str]
    intake_rounds: int
    findings: list[Finding]
    tool_calls: list[dict[str, Any]]
    validator_notes: validator.ValidatorNotes | None
    coverage_rounds: int
    coverage_forced: list[str]
    risk: RiskMemo
    drafts: list[Decision]
    critiques: list[Critique]
    gate: GateResult
    payment: Payment
    resolution: Resolution
    outcome: Outcome
    degraded: list[str]


@dataclass
class Deps:
    """What the nodes need from outside the state: model client, database, policy and run log."""

    llm: LLM
    store: Store
    policy: Policy
    log: RunLog

    @classmethod
    def create(cls, path: Path, db: Path) -> Deps:
        """Fresh model client, store, policy and run log for one invoice."""
        return cls(llm=LLM(), store=Store(db), policy=load_policy(), log=RunLog(path))


def _deps(config: RunnableConfig) -> Deps:
    return config["configurable"]["deps"]


def _toolbox(state: State, deps: Deps) -> ToolBox:
    box = ToolBox(state["invoice"], deps.store, deps.policy)  # type: ignore[arg-type]
    box.findings = {(f.code, f.subject): f for f in state.get("findings", [])}
    box.calls = list(state.get("tool_calls", []))
    return box


def _numbered(findings: list[Finding]) -> list[Finding]:
    return [f.model_copy(update={"id": f"F{n}"}) for n, f in enumerate(findings, 1)]


def _degraded(state: State, stage: str, reason: str | None) -> list[str]:
    """Agents that fell back to rules because no model answer existed; the reason goes to the event log."""
    agents = state.get("degraded", [])
    return agents + [stage] if reason and stage not in agents else agents


def _logged_calls(state: State, box: ToolBox, deps: Deps) -> list[dict[str, Any]]:
    for call in box.calls[len(state.get("tool_calls", [])):]:
        deps.log.emit("tool_call", agent=call["by"], tool=call["tool"], args=call["args"], result=call["result"])
    return box.calls


def load_node(state: State, config: RunnableConfig) -> State:
    """Read the file into text; a file with no text skips straight to an unreadable rejection."""
    path = Path(state["path"])
    try:
        source = read_document(path)
    except UnreadableDocument as exc:
        _deps(config).log.emit("stage", agent="loader", error=str(exc))
        return {"source": "", "invoice": None, "extraction_errors": [str(exc)]}
    _deps(config).log.emit("stage", agent="loader", file=path.name, sha256=file_digest(path), chars=len(source))
    return {"source": source, "intake_rounds": 0, "findings": [], "tool_calls": [], "degraded": []}


def intake_node(state: State, config: RunnableConfig) -> State:
    """Intake agent: extract the invoice, or re-extract with the check's errors."""
    deps = _deps(config)
    invoice, reason = intake.run(deps.llm, state["source"], state.get("invoice"), state.get("extraction_errors", []))
    deps.log.emit("stage", agent="intake", round=state["intake_rounds"] + 1, degraded=reason,
                  invoice=invoice.model_dump() if invoice else None)
    return {"invoice": invoice, "intake_rounds": state["intake_rounds"] + 1,
            "degraded": _degraded(state, "intake", reason)}


def check_node(state: State, config: RunnableConfig) -> State:
    """Extraction check: every value must trace to the document; once it does, apply the code-only rules."""
    deps, invoice = _deps(config), state.get("invoice")
    read_by_rules = "intake" in state.get("degraded", [])
    no_text = ["the document could not be read"]
    errors = no_text if invoice is None else extraction_errors(invoice, state["source"], read_by_rules)
    deps.log.emit("stage", agent="extraction_check", errors=errors)
    if errors or invoice is None:
        return {"extraction_errors": errors}
    return {"extraction_errors": [], "findings": invoice_findings(invoice, state["source"], deps.policy, read_by_rules)}


def after_check(state: State, config: RunnableConfig) -> str:
    """Loop 1: back to intake while retries remain, then give up as unreadable."""
    if not state["extraction_errors"]:
        return "validator"
    if state.get("invoice") and state["intake_rounds"] < _deps(config).policy.max_rounds:
        return "intake"
    return "unreadable"


def _needs_model(deps: Deps, what: str, by_hand: str, source: str, subject: str) -> Finding:
    """Manual entry because no model answered for part of the run; the message says what to do in this mode."""
    then = (f"no API key is set. {by_hand} by hand, or set XAI_API_KEY (export XAI_API_KEY=your-key) and "
            "process it again." if deps.llm.mode == "replay" else
            f"Grok did not answer. {by_hand} by hand, or process it again.")
    return deps.policy.finding("NEEDS_MODEL", f"{what} needs Grok, and {then}", source, subject=subject)


def unreadable_node(state: State, config: RunnableConfig) -> State:
    """Record why the document could not be read: a layout the rules can't read is entered by hand."""
    deps = _deps(config)
    if "intake" in state.get("degraded", []):
        finding = _needs_model(deps, "Reading this layout", "Enter the invoice", "extraction_check", "unreadable")
    else:
        finding = deps.policy.finding("UNREADABLE", "Could not extract a consistent invoice: "
                                      + "; ".join(state["extraction_errors"]), "extraction_check", subject="unreadable")
    return {"findings": _numbered([finding]), "drafts": []}


def validator_node(state: State, config: RunnableConfig) -> State:
    """Validator agent: runs the checks through tools; on a second round, only what coverage found missing."""
    deps = _deps(config)
    box = _toolbox(state, deps)
    missing = box.missing_checks() if state.get("coverage_rounds") else []
    notes, reason = validator.run(deps.llm, state["invoice"], box, missing)  # type: ignore[arg-type]
    deps.log.emit("stage", agent="validator", notes=notes.model_dump() if notes else None, degraded=reason)
    return {"validator_notes": notes or state.get("validator_notes"), "findings": box.finding_list(),
            "tool_calls": _logged_calls(state, box, deps), "degraded": _degraded(state, "validator", reason)}


def coverage_node(state: State, config: RunnableConfig) -> State:
    """Coverage check: on the last round, or if the model is unavailable, code runs the skipped checks itself."""
    deps = _deps(config)
    box = _toolbox(state, deps)
    rounds = state.get("coverage_rounds", 0) + 1
    missing = box.missing_checks()
    forced: list[str] = []
    model_gave_up = "validator" in state.get("degraded", [])
    if missing and (rounds >= deps.policy.max_rounds or model_gave_up):
        forced = [f"{tool}({args})" for tool, args in box.run_missing()]
        missing = []
    deps.log.emit("stage", agent="coverage", round=rounds, missing=[f"{t}({a})" for t, a in missing], forced=forced)
    return {"coverage_rounds": rounds, "coverage_forced": state.get("coverage_forced", []) + forced,
            "findings": _numbered(box.finding_list()), "tool_calls": _logged_calls(state, box, deps)}


def after_coverage(state: State, config: RunnableConfig) -> str:
    """Loop 2: back to the validator while checks are missing and rounds remain."""
    deps = _deps(config)
    if state["coverage_rounds"] >= deps.policy.max_rounds:
        return "risk"
    return "validator" if _toolbox(state, deps).missing_checks() else "risk"


def risk_node(state: State, config: RunnableConfig) -> State:
    """Risk analyst: a memo for the VP, and a FRAUD_SIGNALS finding when it is high with verified quotes."""
    deps = _deps(config)
    box = _toolbox(state, deps)
    memo, reason = risk.run(deps.llm, state["source"], state["invoice"], state["findings"], box)  # type: ignore[arg-type]
    findings = state["findings"]
    extra = risk.finding(memo, deps.policy)
    if extra and not any(f.code == extra.code and f.subject == extra.subject for f in findings):
        findings = _numbered(findings + [extra])
    deps.log.emit("stage", agent="risk", memo=memo.model_dump(), degraded=reason)
    return {"risk": memo, "findings": findings, "drafts": [], "critiques": [],
            "tool_calls": _logged_calls(state, box, deps), "degraded": _degraded(state, "risk", reason)}


def approver_node(state: State, config: RunnableConfig) -> State:
    """VP approver: a first draft, or a revision answering the critic's objections."""
    deps = _deps(config)
    drafts, critiques = state.get("drafts", []), state.get("critiques", [])
    previous = drafts[-1] if drafts else None
    critique = critiques[-1] if critiques else None
    box = _toolbox(state, deps)
    concerns = notes.concerns if (notes := state.get("validator_notes")) else []
    decision, reason = approver.run(deps.llm, state["invoice"], state["findings"], concerns,  # type: ignore[arg-type]
                                    state.get("risk"), box, deps.policy, previous, critique)
    deps.log.emit("stage", agent="approver", draft=len(drafts) + 1, decision=decision.model_dump(), degraded=reason)
    return {"drafts": drafts + [decision], "tool_calls": _logged_calls(state, box, deps),
            "degraded": _degraded(state, "approver", reason)}


def after_approver(state: State, config: RunnableConfig) -> str:
    """Loop 3: the critic reviews the draft when policy calls for it and rounds remain."""
    deps, critiques = _deps(config), state.get("critiques", [])
    draft = state["drafts"][-1]
    if not critiques and not approver.needs_critique(state["invoice"], state["findings"], deps.policy, draft):  # type: ignore[arg-type]
        return "gate"
    return "critic" if len(critiques) < deps.policy.max_rounds else "gate"


def critic_node(state: State, config: RunnableConfig) -> State:
    """Critic: objections to the latest draft, with the vendor master record the VP could look up."""
    deps = _deps(config)
    records = [c["result"] for c in state.get("tool_calls", []) if c["tool"] == "get_vendor"]
    concerns = notes.concerns if (notes := state.get("validator_notes")) else []
    critique, reason = critic.run(deps.llm, state["invoice"], state["findings"], concerns,  # type: ignore[arg-type]
                                  state.get("risk"), state["drafts"][-1], records[-1] if records else None, deps.policy)
    deps.log.emit("stage", agent="critic", round=len(state.get("critiques", [])) + 1,
                  critique=critique.model_dump(), degraded=reason)
    return {"critiques": state.get("critiques", []) + [critique], "degraded": _degraded(state, "critic", reason)}


def after_critic(state: State, config: RunnableConfig) -> str:
    """Back to the VP when the critic wants a revision and rounds remain; otherwise to the gate."""
    revise = state["critiques"][-1].verdict == "revise"
    return "approver" if revise and len(state["critiques"]) < _deps(config).policy.max_rounds else "gate"


def gate_node(state: State, config: RunnableConfig) -> State:
    """Policy gate on the final draft; a run no check rejected but some step made without a model waits for a person."""
    deps, findings = _deps(config), state["findings"]
    decision = state["drafts"][-1]
    unchecked = [f"{tool}({args})" for tool, args in _toolbox(state, deps).missing_checks()]
    result = gate(decision, findings, state["invoice"].total, state.get("critiques", []),  # type: ignore[union-attr]
                  unchecked, bool(state.get("degraded")), deps.policy)
    if NO_MODEL in result.blocked_by and not any(f.severity == Severity.REJECT for f in findings):
        warned = ", ".join(f"{f.id} {f.code}" for f in findings if f.severity == Severity.WARN)
        passed = f"Every check passed except warnings: {warned}." if warned else "Every check passed."
        findings = _numbered(findings + [_needs_model(deps, f"{passed} Approval needs the VP review, which",
                                                      "Approve it", "policy_gate", "approval")])
    deps.log.emit("stage", agent="policy_gate", **result.model_dump(), decision=decision.action)
    return {"gate": result, "findings": findings}


def after_gate(state: State) -> str:
    """Pay only what the gate passed."""
    return "payment" if state["gate"].approved else "resolution"


def payment_node(state: State, config: RunnableConfig) -> State:
    """Payment agent: pay once under the invoice's idempotency key."""
    deps = _deps(config)
    invoice: Invoice = state["invoice"]  # type: ignore[assignment]
    key = payment.idempotency_key(invoice, content_hash(invoice, deps.store.catalog()))
    result = payment.pay(deps.store, invoice, key, deps.policy)
    deps.log.emit("stage", agent="payment", **result.model_dump())
    if result.status == "success":
        outcome = Outcome(status="PAID", amount=result.amount,
                          summary=f"Paid {result.amount:,.2f} to {invoice.vendor}: {state['drafts'][-1].summary}")
    elif result.status == "already_paid":
        outcome = Outcome(status="REJECTED", disposition="void", summary=f"Not paid again: {result.detail}.")
    else:
        outcome = Outcome(status="PAYMENT_FAILED", amount=result.amount,
                          summary=f"Approved, but payment did not go through: {result.detail}")
    return {"payment": result, "outcome": outcome}


def resolution_node(state: State, config: RunnableConfig) -> State:
    """Resolution agent: disposition, audit reasoning and the vendor email; manual entry needs no agent or email."""
    deps = _deps(config)
    forced = required_disposition(state["findings"], deps.policy)
    if forced == "manual_entry":
        summary = " ".join(f.message for f in state["findings"] if deps.policy.findings[f.code].disposition == forced)
        deps.log.emit("stage", agent="resolution", disposition=forced, reasoning=summary)
        return {"outcome": Outcome(status="REJECTED", disposition=forced, summary=summary)}
    drafts = state.get("drafts") or []
    result, reason = resolution.run(deps.llm, state.get("invoice"), state["findings"], drafts[-1] if drafts else None,
                                    forced)
    deps.log.emit("stage", agent="resolution", **result.model_dump(), degraded=reason)
    return {"resolution": result, "degraded": _degraded(state, "resolution", reason),
            "outcome": Outcome(status="REJECTED", disposition=result.disposition, summary=result.reasoning)}


def record_node(state: State, config: RunnableConfig) -> State:
    """Write the ledger row, the outcome event, report.md and state.json."""
    deps, invoice, outcome = _deps(config), state.get("invoice"), state["outcome"]
    catalog = deps.store.catalog()
    deps.store.record_invoice(
        number=invoice.invoice_number if invoice else None,
        number_key=number_key(invoice.invoice_number) if invoice else "",
        vendor=invoice.vendor if invoice else None,
        vendor_key=text_key(invoice.vendor) if invoice else "",
        content_hash=content_hash(invoice, catalog) if invoice else "",
        status=outcome.status, disposition=outcome.disposition, total=invoice.total if invoice else None,
        currency=invoice.currency if invoice else None, source_file=Path(state["path"]).name,
        run_id=deps.log.run_id, lines=[li.model_dump() for li in invoice.line_items] if invoice else [],
    )
    deps.log.emit("outcome", **outcome.model_dump(), degraded=state.get("degraded", []), **deps.log.totals())
    write_report(deps.log, dict(state))
    save_state(deps.log, dict(state))
    return {}
