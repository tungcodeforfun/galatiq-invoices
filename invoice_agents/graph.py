"""The LangGraph state graph: seven agents, three bounded self-correction loops, the policy gate, the ledger."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from invoice_agents import nodes
from invoice_agents.nodes import Deps, State


def build_graph() -> Any:
    """Compile the graph. Loops: intake ⇄ check, validator ⇄ coverage, approver ⇄ critic, each bounded by policy."""
    g = StateGraph(State)
    for name, node in [("load", nodes.load_node), ("intake", nodes.intake_node), ("check", nodes.check_node),
                       ("unreadable", nodes.unreadable_node), ("validator", nodes.validator_node),
                       ("coverage", nodes.coverage_node), ("risk", nodes.risk_node),
                       ("approver", nodes.approver_node), ("critic", nodes.critic_node), ("gate", nodes.gate_node),
                       ("payment", nodes.payment_node), ("resolution", nodes.resolution_node),
                       ("record", nodes.record_node)]:
        g.add_node(name, node)
    g.add_edge(START, "load")
    g.add_conditional_edges("load", lambda s: "intake" if s.get("source") else "unreadable")
    g.add_edge("intake", "check")
    g.add_conditional_edges("check", nodes.after_check)
    g.add_edge("unreadable", "resolution")
    g.add_edge("validator", "coverage")
    g.add_conditional_edges("coverage", nodes.after_coverage)
    g.add_edge("risk", "approver")
    g.add_conditional_edges("approver", nodes.after_approver)
    g.add_conditional_edges("critic", nodes.after_critic)
    g.add_conditional_edges("gate", nodes.after_gate)
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
