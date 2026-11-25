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
from invoice_agents.fallback import notice
from invoice_agents.graph import stream
from invoice_agents.llm import LLM
from invoice_agents.matching import invoice_key
from invoice_agents.nodes import Deps
from invoice_agents.observability import RUNS_DIR, load_state
from main import SUFFIXES, step_line
from ui.words import call_in_words

STAGES = [("intake", "Intake"), ("validator", "Validator"), ("risk", "Risk"), ("approver", "VP"),
          ("critic", "Critic"), ("gate", "Gate"), ("payment", "Payment"), ("resolution", "Resolution")]
SEVERITY_COLOR = {"reject": "red", "warn": "orange", "info": "blue"}
RISK_COLOR = {"low": "green", "medium": "orange", "high": "red"}

st.set_page_config(page_title="Accounts payable agents", page_icon=":material/receipt_long:", layout="wide")


def samples() -> list[Path]:
    """Every sample and extra invoice shipped in data/."""
    return sorted(p for d in ("data/invoices", "data/invoices_extra") for p in (ROOT / d).iterdir()
                  if p.suffix.lower() in SUFFIXES)


def money(value: float | None, currency: str | None = None) -> str:
    """Money with its currency code when it isn't USD; a dash when missing."""
    if value is None:
        return "—"
    return f"{value:,.2f}" + (f" {currency}" if currency and currency != "USD" else "")


def stage_strip(done: dict[str, str]) -> str:
    """One badge per agent: grey until it runs, then green, red or blue for what it concluded."""
    return " ".join(f":{done.get(key, 'gray')}-badge[{label}]" for key, label in STAGES)


def stage_color(node: str, s: Any) -> str:
    """Badge color for a finished agent: green for go, red for stop, orange for caution."""
    if node == "approver":
        return "green" if s["drafts"][-1].action == "approve" else "red"
    if node == "critic":
        return "green" if s["critiques"][-1].verdict == "accept" else "orange"
    if node == "gate":
        return "green" if s["gate"].approved else "red"
    if node == "risk":
        return RISK_COLOR[s["risk"].level]
    if node == "payment":
        return "green" if s["payment"].status in ("success", "already_paid") else "orange"
    return "red" if node == "resolution" else "blue"


def process(path: Path) -> str:
    """Run one invoice, updating the agent strip and step log as each node finishes. Returns the run ID."""
    deps = Deps.create(path, DEFAULT_DB)
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
    """Paid, rejected or failed, with the one-paragraph reason and any degraded-mode note."""
    out = s["outcome"]
    title = out["status"].replace("_", " ").title() + (f" · {out['disposition'].replace('_', ' ')}"
                                                       if out["disposition"] else "")
    {"PAID": st.success, "REJECTED": st.error}.get(out["status"], st.warning)(f"**{title}**  \n{out['summary']}")
    if s.get("degraded"):
        live = "live" in s.get("totals", {}).get("tiers", [])
        st.warning(notice(s["degraded"], live, reset="**Reset ledger** in the sidebar"))


def findings_table(findings: list[dict[str, Any]]) -> None:
    """One line per finding, colored by severity."""
    if not findings:
        st.caption("No findings")
        return
    for f in findings:
        color = SEVERITY_COLOR[f["severity"]]
        st.markdown(f":{color}-badge[{f['severity']}] **{f['id']} {f['code']}** {f['message']}")


def document_view(s: dict[str, Any]) -> None:
    """The source document beside the extracted fields, line items and corrections."""
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


def review_view(s: dict[str, Any]) -> None:
    """VP drafts, each followed by the critic's answer to it."""
    critiques = s.get("critiques") or []
    for n, draft in enumerate(s.get("drafts") or [], 1):
        with st.chat_message("VP", avatar=":material/gavel:"):
            st.markdown(f"**VP draft {n}: {draft['action']}**  \n{draft['summary']}")
            for r in draft["reasons"]:
                st.markdown(f"- {r['text']}" + (f" ({', '.join(r['finding_ids'])})" if r["finding_ids"] else ""))
        if n <= len(critiques):
            c = critiques[n - 1]
            with st.chat_message("Critic", avatar=":material/rate_review:"):
                st.markdown(f"**Critic: {c['verdict']}**")
                for o in c["objections"]:
                    st.markdown(f"- {o}")


def agents_view(s: dict[str, Any]) -> None:
    """The agent transcript: tool calls, risk memo, VP drafts and critiques, gate, payment."""
    calls = s.get("tool_calls") or []
    if calls:
        st.markdown("**Tool calls**")
        st.dataframe(pd.DataFrame([call_in_words(c) for c in calls]), hide_index=True, width="stretch")
    if s.get("coverage_forced"):
        st.markdown("Coverage ran in code: " + ", ".join(s["coverage_forced"]))
    if s.get("risk"):
        memo = s["risk"]
        st.markdown(f"**Risk analyst** :{RISK_COLOR[memo['level']]}-badge[{memo['level']}]  \n{memo['summary']}")
        for sig in memo["signals"]:
            st.markdown(f"- {sig['kind'].replace('_', ' ')}: “{sig['quote']}” {sig['why']}")
    review_view(s)
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
    recorded = "live" not in t.get("tiers", [])
    cols = st.columns(5)
    cols[0].metric("Total", money(inv.get("total"), inv.get("currency")))
    cols[1].metric("Findings", len(s.get("findings") or []))
    cols[2].metric("Model / tool calls", f"{t.get('llm_calls', 0)} / {t.get('tool_calls', 0)}")
    cols[3].metric("Grok cost" + (" (recorded)" if recorded else ""), f"${t.get('cost_usd', 0):.4f}")
    cols[4].metric("Time" + (" (recorded)" if recorded else ""), f"{t.get('seconds', 0)} s")
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
    """The ledger as a table, newest first."""
    rows = store.ledger()
    return pd.DataFrame([{"File": r["source_file"], "Invoice": r["number"], "Vendor": r["vendor"],
                          "Total": r["total"], "Currency": r["currency"] or "USD", "Outcome": r["status"],
                          "Disposition": (r["disposition"] or "").replace("_", " "), "run_id": r["run_id"]}
                         for r in rows])


def decisions(store: Store) -> None:
    """Decisions tab: totals, filters, the ledger, and the full run for the selected row."""
    frame = ledger_frame(store)
    if frame.empty:
        st.info("No invoices processed yet. Process one from the Inbox tab, or run `python main.py demo`.")
        return
    paid = frame[frame.Outcome == "PAID"]
    rejected = frame[frame.Outcome == "REJECTED"]
    usd = rejected[(rejected.Currency == "USD") & (rejected.Total > 0)]
    once = usd[~pd.Series([invoice_key(v, n) for v, n in zip(usd.Vendor, usd.Invoice, strict=True)],
                          index=usd.index, dtype=str).duplicated()]
    cols = st.columns(4)
    cols[0].metric("Processed", len(frame))
    cols[1].metric(f"Paid · {len(paid)}", f"${paid.Total.sum():,.0f}")
    cols[2].metric(f"Rejected · {len(rejected)}", f"${once.Total.sum():,.0f}",
                   help="USD stopped from going out, each invoice number counted once")
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
    st.caption("Select a row to see the full run.")
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


def inbox() -> None:
    """Inbox tab: pick or upload an invoice, process it, and show the run."""
    source = st.radio("Invoice", ["Sample", "Upload"], horizontal=True, label_visibility="collapsed")
    pick, button = st.columns([3, 1], vertical_alignment="bottom")
    path: Path | None = None
    with pick:
        if source == "Sample":
            path = st.selectbox("Sample invoice", samples(), format_func=lambda p: f"{p.parent.name}/{p.name}")
        else:
            upload = st.file_uploader("Invoice file", type=[s.lstrip(".") for s in SUFFIXES])
            if upload:
                folder = RUNS_DIR / "uploads"
                folder.mkdir(parents=True, exist_ok=True)
                path = folder / Path(upload.name).name
                path.write_bytes(upload.getvalue())
    go = button.button("Process invoice", type="primary", disabled=path is None, width="stretch")
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
    """Model mode and the reset control."""
    with st.sidebar:
        st.markdown("### Acme accounts payable")
        llm = LLM()
        if llm.mode == "live":
            st.markdown(f":green-badge[Live] {llm.model}")
        else:
            st.markdown(f":blue-badge[Replay] recorded {llm.model} responses")
        with st.popover("Reset ledger", width="stretch"):
            st.markdown("Clears every processed invoice and payment.")
            if st.button("Reset", type="primary"):
                store.reset()
                st.session_state.pop("last_run", None)
                st.rerun()


def main() -> None:
    """Render the dashboard."""
    store = Store(DEFAULT_DB)
    sidebar(store)
    inbox_tab, decisions_tab = st.tabs(["Inbox", "Decisions"])
    with inbox_tab:
        inbox()
    with decisions_tab:
        decisions(store)


main()
