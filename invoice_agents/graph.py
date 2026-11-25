"""The LangGraph state graph: seven agents, three bounded self-correction loops, the policy gate, the ledger."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from invoice_agents.agents import approver, critic, intake, payment, resolution, risk, validator
from invoice_agents.db import Store
from invoice_agents.llm import LLM
from invoice_agents.loaders import UnreadableDocument, file_digest, read_document
from invoice_agents.observability import RunLog, save_state, write_report
from invoice_agents.policy import GateResult, Policy, gate
from invoice_agents.rules import extraction_errors, invoice_findings
from invoice_agents.schema import Critique, Decision, Finding, Invoice, Outcome, Payment, Resolution, RiskMemo
from invoice_agents.tools import ToolBox, content_hash, number_key, text_key


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
    risk: RiskMemo | None
    drafts: list[Decision]
    critiques: list[Critique]
    gate: GateResult
    payment: Payment | None
    resolution: Resolution | None
    outcome: Outcome
    degraded: list[str]


@dataclass
class Deps:
    """What the nodes need from outside the state: model client, database, policy and run log."""

    llm: LLM
    store: Store
    policy: Policy
    log: RunLog


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
    return state.get("degraded", []) + ([f"{stage}: {reason}"] if reason else [])


def load_node(state: State, config: RunnableConfig) -> State:
    path = Path(state["path"])
    try:
        source = read_document(path)
    except UnreadableDocument as exc:
        _deps(config).log.emit("stage", agent="loader", error=str(exc))
        return {"source": "", "invoice": None, "extraction_errors": [str(exc)], "intake_rounds": 99}
    _deps(config).log.emit("stage", agent="loader", file=path.name, sha256=file_digest(path), chars=len(source))
    return {"source": source, "intake_rounds": 0, "findings": [], "tool_calls": [], "degraded": []}


def intake_node(state: State, config: RunnableConfig) -> State:
    deps = _deps(config)
    invoice, reason = intake.run(deps.llm, state["source"], state.get("invoice"), state.get("extraction_errors", []))
    deps.log.emit("stage", agent="intake", round=state["intake_rounds"] + 1, degraded=reason,
                  invoice=invoice.model_dump() if invoice else None)
    return {"invoice": invoice, "intake_rounds": state["intake_rounds"] + 1,
            "degraded": _degraded(state, "intake", reason)}


def check_node(state: State, config: RunnableConfig) -> State:
    deps, invoice = _deps(config), state.get("invoice")
    no_text = ["the document could not be read"]
    errors = no_text if invoice is None else extraction_errors(invoice, state["source"])
    deps.log.emit("stage", agent="extraction_check", errors=errors)
    if errors or invoice is None:
        return {"extraction_errors": errors}
    return {"extraction_errors": [], "findings": invoice_findings(invoice, state["source"], deps.policy)}


def after_check(state: State, config: RunnableConfig) -> str:
    if not state["extraction_errors"]:
        return "validator"
    if state.get("invoice") and state["intake_rounds"] <= _deps(config).policy.max_rounds:
        return "intake"
    return "unreadable"


def unreadable_node(state: State, config: RunnableConfig) -> State:
    deps = _deps(config)
    finding = deps.policy.finding("UNREADABLE", "Could not extract a consistent invoice: "
                                  + "; ".join(state["extraction_errors"]), "extraction_check", subject="unreadable")
    return {"findings": _numbered([finding]), "drafts": []}


def validator_node(state: State, config: RunnableConfig) -> State:
    deps = _deps(config)
    box = _toolbox(state, deps)
    missing = box.missing_checks() if state.get("coverage_rounds") else []
    notes, reason = validator.run(deps.llm, state["invoice"], box, missing)  # type: ignore[arg-type]
    for call in box.calls[len(state.get("tool_calls", [])):]:
        deps.log.emit("tool_call", agent="validator", **call)
    deps.log.emit("stage", agent="validator", notes=notes.model_dump() if notes else None, degraded=reason)
    return {"validator_notes": notes or state.get("validator_notes"), "findings": box.finding_list(),
            "tool_calls": box.calls, "degraded": _degraded(state, "validator", reason)}


def coverage_node(state: State, config: RunnableConfig) -> State:
    deps = _deps(config)
    box = _toolbox(state, deps)
    rounds = state.get("coverage_rounds", 0) + 1
    missing = box.missing_checks()
    forced: list[str] = []
    model_gave_up = bool(state.get("degraded")) and state["degraded"][-1].startswith("validator")
    if missing and (rounds >= deps.policy.max_rounds or model_gave_up):
        forced = [f"{tool}({args})" for tool, args in box.run_missing()]
        missing = []
    deps.log.emit("stage", agent="coverage", round=rounds, missing=[f"{t}({a})" for t, a in missing], forced=forced)
    return {"coverage_rounds": rounds, "coverage_forced": state.get("coverage_forced", []) + forced,
            "findings": _numbered(box.finding_list()), "tool_calls": box.calls}


def after_coverage(state: State, config: RunnableConfig) -> str:
    deps = _deps(config)
    if state["coverage_rounds"] >= deps.policy.max_rounds:
        return "risk"
    return "validator" if _toolbox(state, deps).missing_checks() else "risk"


def risk_node(state: State, config: RunnableConfig) -> State:
    deps = _deps(config)
    box = _toolbox(state, deps)
    memo, reason = risk.run(deps.llm, state["source"], state["invoice"], state["findings"], box)  # type: ignore[arg-type]
    findings = state["findings"]
    extra = risk.finding(memo, deps.policy)
    if extra and not any(f.code == extra.code and f.subject == extra.subject for f in findings):
        findings = _numbered(findings + [extra])
    deps.log.emit("stage", agent="risk", memo=memo.model_dump(), degraded=reason)
    return {"risk": memo, "findings": findings, "drafts": [], "critiques": [],
            "degraded": _degraded(state, "risk", reason)}


def approver_node(state: State, config: RunnableConfig) -> State:
    deps = _deps(config)
    drafts, critiques = state.get("drafts", []), state.get("critiques", [])
    previous = drafts[-1] if drafts else None
    critique = critiques[-1] if critiques else None
    decision, reason = approver.run(deps.llm, state["invoice"], state["findings"], state.get("risk"),  # type: ignore[arg-type]
                                    _toolbox(state, deps), deps.policy, previous, critique)
    deps.log.emit("stage", agent="approver", draft=len(drafts) + 1, decision=decision.model_dump(), degraded=reason)
    return {"drafts": drafts + [decision], "degraded": _degraded(state, "approver", reason)}


def after_approver(state: State, config: RunnableConfig) -> str:
    deps, critiques = _deps(config), state.get("critiques", [])
    if not critiques and not approver.needs_critique(state["invoice"], state["findings"], deps.policy):  # type: ignore[arg-type]
        return "gate"
    return "critic" if len(critiques) < deps.policy.max_rounds else "gate"


def critic_node(state: State, config: RunnableConfig) -> State:
    deps = _deps(config)
    critique, reason = critic.run(deps.llm, state["invoice"], state["findings"], state.get("risk"),  # type: ignore[arg-type]
                                  state["drafts"][-1], deps.policy)
    deps.log.emit("stage", agent="critic", round=len(state.get("critiques", [])) + 1,
                  critique=critique.model_dump(), degraded=reason)
    return {"critiques": state.get("critiques", []) + [critique], "degraded": _degraded(state, "critic", reason)}


def after_critic(state: State, config: RunnableConfig) -> str:
    revise = state["critiques"][-1].verdict == "revise"
    return "approver" if revise and len(state["critiques"]) < _deps(config).policy.max_rounds else "gate"


def gate_node(state: State, config: RunnableConfig) -> State:
    deps = _deps(config)
    decision = state["drafts"][-1]
    result = gate(decision, state["findings"], state["invoice"].total, len(state.get("critiques", [])),  # type: ignore[union-attr]
                  bool(state.get("degraded")), deps.policy)
    deps.log.emit("stage", agent="policy_gate", **result.model_dump(), decision=decision.action)
    return {"gate": result}


def after_gate(state: State) -> str:
    return "payment" if state["gate"].approved else "resolution"


def payment_node(state: State, config: RunnableConfig) -> State:
    deps = _deps(config)
    invoice: Invoice = state["invoice"]  # type: ignore[assignment]
    key = payment.idempotency_key(invoice, content_hash(invoice, deps.store.catalog()))
    result = payment.pay(deps.store, invoice, key, deps.policy)
    deps.log.emit("stage", agent="payment", **result.model_dump())
    if result.status in ("success", "already_paid"):
        outcome = Outcome(status="PAID", amount=result.amount,
                          summary=f"Paid {result.amount:,.2f} to {invoice.vendor}: {state['drafts'][-1].summary}")
    else:
        outcome = Outcome(status="PAYMENT_FAILED", amount=result.amount,
                          summary=f"Approved, but payment did not go through: {result.detail}")
    return {"payment": result, "outcome": outcome}


def resolution_node(state: State, config: RunnableConfig) -> State:
    deps = _deps(config)
    drafts = state.get("drafts") or []
    result, reason = resolution.run(deps.llm, state.get("invoice"), state["findings"], drafts[-1] if drafts else None,
                                    deps.policy)
    deps.log.emit("stage", agent="resolution", **result.model_dump(), degraded=reason)
    return {"resolution": result, "degraded": _degraded(state, "resolution", reason),
            "outcome": Outcome(status="REJECTED", disposition=result.disposition, summary=result.reasoning)}


def record_node(state: State, config: RunnableConfig) -> State:
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


def build_graph() -> Any:
    """Compile the graph. Loops: intake ⇄ check, validator ⇄ coverage, approver ⇄ critic, each bounded by policy."""
    g = StateGraph(State)
    for name, node in [("load", load_node), ("intake", intake_node), ("check", check_node),
                       ("unreadable", unreadable_node), ("validator", validator_node), ("coverage", coverage_node),
                       ("risk", risk_node), ("approver", approver_node), ("critic", critic_node),
                       ("gate", gate_node), ("payment", payment_node), ("resolution", resolution_node),
                       ("record", record_node)]:
        g.add_node(name, node)
    g.add_edge(START, "load")
    g.add_conditional_edges("load", lambda s: "intake" if s.get("source") else "unreadable")
    g.add_edge("intake", "check")
    g.add_conditional_edges("check", after_check)
    g.add_edge("unreadable", "resolution")
    g.add_edge("validator", "coverage")
    g.add_conditional_edges("coverage", after_coverage)
    g.add_edge("risk", "approver")
    g.add_conditional_edges("approver", after_approver)
    g.add_conditional_edges("critic", after_critic)
    g.add_conditional_edges("gate", after_gate)
    g.add_edge("payment", "record")
    g.add_edge("resolution", "record")
    g.add_edge("record", END)
    return g.compile()


GRAPH = build_graph()


def stream(path: Path, deps: Deps) -> Iterator[tuple[str, State]]:
    """Run one invoice, yielding (node, accumulated state) after each step for live progress displays."""
    deps.llm.on_call = deps.log.llm_call
    deps.log.emit("start", file=path.name, llm_mode=deps.llm.mode, model=deps.llm.model)
    state: State = {"path": str(path)}
    config: RunnableConfig = {"configurable": {"deps": deps}, "recursion_limit": 60}
    for update in GRAPH.stream(state, config, stream_mode="updates"):
        for node, change in update.items():
            state.update(change or {})  # type: ignore[typeddict-item]
            yield node, state


def process(path: Path, deps: Deps) -> State:
    """Run one invoice to its outcome."""
    final: State = {}
    for _, state in stream(path, deps):
        final = state
    return final
