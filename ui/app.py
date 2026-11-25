"""Streamlit dashboard: process an invoice and watch the agents work, review every decision, read any run in full."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from invoice_agents.db import DEFAULT_DB, Store
from invoice_agents.graph import stream
from invoice_agents.llm import LLM
from invoice_agents.observability import RUNS_DIR, load_state
from main import SUFFIXES, make_deps, step_line

STAGES = [("intake", "Intake"), ("validator", "Validator"), ("risk", "Risk"), ("approver", "VP"),
          ("critic", "Critic"), ("gate", "Gate"), ("payment", "Payment"), ("resolution", "Resolution")]
SEVERITY_COLOR = {"reject": "red", "warn": "orange", "info": "blue"}
STATUS_COLOR = {"PAID": "green", "REJECTED": "red", "PAYMENT_FAILED": "orange"}

st.set_page_config(page_title="Accounts payable agents", page_icon=":material/receipt_long:", layout="wide")


def samples() -> list[Path]:
    return sorted(p for d in ("data/invoices", "data/invoices_extra") for p in (ROOT / d).iterdir()
                  if p.suffix.lower() in SUFFIXES)


def money(value: float | None, currency: str | None = None) -> str:
    if value is None:
        return "—"
    return f"{value:,.2f}" + (f" {currency}" if currency and currency != "USD" else "")


def stage_strip(done: dict[str, str]) -> str:
    """One badge per agent: grey until it runs, then green, red or blue for what it concluded."""
    return " ".join(f":{done.get(key, 'gray')}-badge[{label}]" for key, label in STAGES)


def stage_color(node: str, s: Any) -> str:
    if node == "approver":
        return "green" if s["drafts"][-1].action == "approve" else "red"
    if node == "critic":
        return "green" if s["critiques"][-1].verdict == "accept" else "orange"
    if node == "gate":
        return "green" if s["gate"].approved else "red"
    if node == "risk":
        return {"low": "green", "medium": "orange", "high": "red"}[s["risk"].level]
    if node == "payment":
        return "green" if s["payment"].status in ("success", "already_paid") else "orange"
    return "red" if node == "resolution" else "blue"


def process(path: Path) -> str:
    """Run one invoice, updating the agent strip and step log as each node finishes. Returns the run ID."""
    deps = make_deps(path, DEFAULT_DB)
    strip = st.empty()
    done: dict[str, str] = {}
    strip.markdown(stage_strip(done))
    with st.status(f"Processing {path.name}", expanded=True) as status:
        for node, state in stream(path, deps):
            if node in dict(STAGES):
                done[node] = stage_color(node, state)
                strip.markdown(stage_strip(done))
            line = step_line(node, state)
            if line:
                status.write(line)
        out = state["outcome"]
        status.update(label=f"{path.name}: {out.status}", state="complete", expanded=False)
    return deps.log.run_id


def outcome_banner(s: dict[str, Any]) -> None:
    out = s["outcome"]
    title = out["status"].replace("_", " ").title() + (f" · {out['disposition'].replace('_', ' ')}"
                                                       if out["disposition"] else "")
    {"PAID": st.success, "REJECTED": st.error}.get(out["status"], st.warning)(f"**{title}**  \n{out['summary']}")
    if s.get("degraded"):
        st.warning("Degraded mode: " + "; ".join(s["degraded"]))


def findings_table(findings: list[dict[str, Any]]) -> None:
    if not findings:
        st.caption("No findings")
        return
    for f in findings:
        color = SEVERITY_COLOR[f["severity"]]
        st.markdown(f":{color}-badge[{f['severity']}] **{f['id']} {f['code']}** {f['message']}")


def document_view(s: dict[str, Any]) -> None:
    left, right = st.columns(2)
    with left:
        st.markdown("**Source document**")
        st.code(s.get("source") or "", language=None, wrap_lines=True, height=460)
    with right:
        inv = s.get("invoice")
        st.markdown("**Extracted**")
        if not inv:
            st.caption("Nothing could be extracted")
            return
        fields = {k: v for k, v in inv.items() if k not in ("line_items", "corrections") and v not in (None, "")}
        st.dataframe(pd.DataFrame({"field": list(fields), "value": [str(v) for v in fields.values()]}),
                     hide_index=True, width="stretch")
        st.dataframe(pd.DataFrame(inv["line_items"]), hide_index=True, width="stretch")
        for c in inv["corrections"]:
            st.markdown(f":blue-badge[corrected] {c['field']}: `{c['as_written']}` read as `{c['normalized']}`")


def agents_view(s: dict[str, Any]) -> None:
    calls = s.get("tool_calls") or []
    if calls:
        st.markdown("**Validator tool calls**")
        st.dataframe(pd.DataFrame([{"by": c["by"], "tool": c["tool"], "args": str(c["args"]),
                                    "result": str(c["result"])} for c in calls]),
                     hide_index=True, width="stretch")
    if s.get("coverage_forced"):
        st.markdown("Coverage ran in code: " + ", ".join(s["coverage_forced"]))
    if s.get("risk"):
        memo = s["risk"]
        st.markdown(f"**Risk analyst** :{ {'low': 'green', 'medium': 'orange', 'high': 'red'}[memo['level']] }"
                    f"-badge[{memo['level']}]  \n{memo['summary']}")
        for sig in memo["signals"]:
            st.markdown(f"- {sig['kind'].replace('_', ' ')}: “{sig['quote']}” {sig['why']}")
    critiques = s.get("critiques") or []
    for n, draft in enumerate(s.get("drafts") or [], 1):
        with st.chat_message("VP", avatar=":material/gavel:"):
            st.markdown(f"**Draft {n}: {draft['action']}**  \n{draft['summary']}")
            for r in draft["reasons"]:
                st.markdown(f"- {r['text']}" + (f" ({', '.join(r['finding_ids'])})" if r["finding_ids"] else ""))
        if n <= len(critiques):
            c = critiques[n - 1]
            with st.chat_message("Critic", avatar=":material/rate_review:"):
                st.markdown(f"**{c['verdict'].title()}**")
                for o in c["objections"]:
                    st.markdown(f"- {o}")
    if s.get("gate"):
        g = s["gate"]
        st.markdown("**Policy gate:** " + ("pass" if g["approved"] else "blocked by " + ", ".join(g["blocked_by"])))
    if s.get("payment"):
        p = s["payment"]
        st.markdown(f"**Payment:** {p['status']} · {money(p['amount'])} · attempt {p['attempts']} · "
                    f"key `{p['idempotency_key']}`")


def detail(s: dict[str, Any]) -> None:
    """Everything about one run: outcome, findings, document beside extraction, agent transcript, vendor reply."""
    outcome_banner(s)
    t = s.get("totals", {})
    inv = s.get("invoice") or {}
    cols = st.columns(4)
    cols[0].metric("Total", money(inv.get("total"), inv.get("currency")))
    cols[1].metric("Findings", len(s.get("findings") or []))
    cols[2].metric("Model calls", f"{t.get('llm_calls', 0)} {'/'.join(t.get('tiers', []))}")
    cols[3].metric("Seconds", t.get("seconds", 0))
    tabs = st.tabs(["Findings", "Document", "Agents", "Vendor reply"])
    with tabs[0]:
        findings_table(s.get("findings") or [])
    with tabs[1]:
        document_view(s)
    with tabs[2]:
        agents_view(s)
    with tabs[3]:
        reply = (s.get("resolution") or {}).get("vendor_reply")
        if reply:
            st.code(reply, language=None, wrap_lines=True)
        else:
            st.caption("No reply: the invoice was paid or voided")


def ledger_frame(store: Store) -> pd.DataFrame:
    rows = store.ledger()
    return pd.DataFrame([{"File": r["source_file"], "Invoice": r["number"], "Vendor": r["vendor"],
                          "Total": r["total"], "Currency": r["currency"] or "USD", "Outcome": r["status"],
                          "Disposition": (r["disposition"] or "").replace("_", " "), "run_id": r["run_id"]}
                         for r in rows])


def decisions(store: Store) -> None:
    frame = ledger_frame(store)
    if frame.empty:
        st.info("No invoices processed yet. Process one from the Inbox tab, or run `python main.py demo`.")
        return
    paid = frame[frame.Outcome == "PAID"]
    rejected = frame[frame.Outcome == "REJECTED"]
    usd = rejected[(rejected.Currency == "USD") & (rejected.Total > 0)]
    cols = st.columns(4)
    cols[0].metric("Processed", len(frame))
    cols[1].metric("Paid", f"{len(paid)} · ${paid.Total.sum():,.0f}")
    cols[2].metric("Rejected", f"{len(rejected)} · ${usd.Total.sum():,.0f} stopped")
    cols[3].metric("Straight-through", f"{len(paid) / len(frame):.0%}")
    left, right = st.columns([1, 2])
    status = left.segmented_control("Outcome", ["PAID", "REJECTED", "PAYMENT_FAILED"], selection_mode="multi",
                                    default=["PAID", "REJECTED", "PAYMENT_FAILED"],
                                    format_func=lambda s: s.replace("_", " ").capitalize())
    query = right.text_input("Search", placeholder="Vendor, invoice number or file")
    view = frame[frame.Outcome.isin(status or [])]
    if query:
        mask = view[["File", "Invoice", "Vendor"]].astype(str).apply(lambda c: c.str.contains(query, case=False))
        view = view[mask.any(axis=1)]
    picked = st.dataframe(view.drop(columns="run_id"), hide_index=True, width="stretch",
                          on_select="rerun", selection_mode="single-row",
                          column_config={"Total": st.column_config.NumberColumn(format="%.2f")})
    rows = picked.selection.rows
    if rows:
        state = load_state(RUNS_DIR / view.iloc[rows[0]].run_id)
        st.divider()
        if state:
            detail(state)
        else:
            st.warning("The run log for this invoice is missing.")
    else:
        st.caption("Select a row to see the full run.")


def inbox() -> None:
    left, right = st.columns([1, 2], gap="large")
    with left:
        source = st.radio("Invoice", ["Sample", "Upload"], horizontal=True, label_visibility="collapsed")
        path: Path | None = None
        if source == "Sample":
            files = samples()
            path = st.selectbox("Sample invoice", files, format_func=lambda p: f"{p.parent.name}/{p.name}")
        else:
            upload = st.file_uploader("Invoice file", type=[s.lstrip(".") for s in SUFFIXES])
            if upload:
                folder = RUNS_DIR / "uploads"
                folder.mkdir(parents=True, exist_ok=True)
                path = folder / Path(upload.name).name
                path.write_bytes(upload.getvalue())
        go = st.button("Process invoice", type="primary", disabled=path is None, width="stretch")
    with right:
        if go and path:
            st.session_state["last_run"] = process(path)
        run_id = st.session_state.get("last_run")
        state = load_state(RUNS_DIR / run_id) if run_id else None
        if state:
            detail(state)
        elif not go:
            st.markdown(stage_strip({}))
            st.caption("Pick an invoice and process it to watch each agent work.")


def sidebar(store: Store) -> None:
    with st.sidebar:
        st.markdown("### Acme accounts payable")
        mode = LLM().mode
        st.markdown(f":{'green' if mode == 'live' else 'blue'}-badge[{mode}] model calls")
        with st.popover("Reset ledger", width="stretch"):
            st.markdown("Clears every processed invoice and payment.")
            if st.button("Reset", type="primary"):
                store.reset()
                st.session_state.pop("last_run", None)
                st.rerun()


def main() -> None:
    store = Store(DEFAULT_DB)
    sidebar(store)
    inbox_tab, decisions_tab = st.tabs(["Inbox", "Decisions"])
    with inbox_tab:
        inbox()
    with decisions_tab:
        decisions(store)


main()
