"""Pages and layout for the BOGCL dashboard."""
from __future__ import annotations

import hmac

import pandas as pd
import streamlit as st

import components as C
import data
import genie_client
import map_view
import theme

REQUIRED_SECRETS = ["DATABRICKS_HOST", "DATABRICKS_TOKEN", "DATABRICKS_WAREHOUSE_ID", "GENIE_SPACE_ID"]
MAX_QUESTIONS_PER_SESSION = 20
MAX_QUESTION_CHARS = 600
ALL = "All Vessels"

EXAMPLE_QUESTIONS = [
    "Which vessels are expected to arrive in the next 48 hours?",
    "Which berths are free right now?",
    "Which tanks are above 90% full?",
    "Show delays by cause for the last 7 days",
    "What are the critical alerts from the last 24 hours?",
    "How much cargo has been transferred today?",
]


# --------------------------------------------------------------------------- setup
def inject_css(mode: str) -> None:
    st.html(f'<div class="css-host"></div><style>{theme.build_css(mode)}</style>')


def check_secrets() -> None:
    try:
        missing = [k for k in REQUIRED_SECRETS if k not in st.secrets]
    except Exception:
        missing = REQUIRED_SECRETS
    if missing:
        st.html(C.note("This app is not configured yet. Missing secrets: " + ", ".join(missing), "warn"))
        st.html(C.note("Add them under App settings > Secrets (Streamlit Cloud) or in .streamlit/secrets.toml (local)."))
        st.stop()


def password_gate() -> None:
    """Optional. Set APP_PASSWORD in secrets to put a password in front of the app."""
    expected = st.secrets.get("APP_PASSWORD", "")
    if not expected or st.session_state.get("authed"):
        return
    st.html('<div class="bc bc-card" style="max-width:420px"><div class="bc-title">BOGCL Marine Operations</div>'
            '<div class="bc-tag">Enter the access password to continue.</div></div>')
    pw = st.text_input("Password", type="password", label_visibility="collapsed", placeholder="Password")
    if pw:
        if hmac.compare_digest(pw.encode(), expected.encode()):
            st.session_state["authed"] = True
            st.rerun()
        st.html(C.note("Wrong password.", "bad"))
    st.stop()


def load(fn, *args):
    """Run one data query. A failing panel shows a short notice instead of crashing the page."""
    try:
        return fn(*args)
    except Exception as exc:
        st.html(C.note(f"Could not load {fn.__name__}: {exc}", "bad"))
        return None


def selected_vessel() -> str | None:
    v = st.session_state.get("vessel", ALL)
    return None if v in (None, ALL) else v


# --------------------------------------------------------------------------- top bar
def header(vdf: pd.DataFrame | None) -> None:
    head = load(data.header)
    if head is not None and not head.empty:
        h = head.iloc[0]
        today, clock, alerts_count = str(h.today), str(h.clock), int(h.open_alerts)
    else:
        today, clock, alerts_count = "Date unavailable", "Time unavailable", 0

    # Preserve the existing visual style. The HTML chips used to overflow out of the
    # brand's column and sit on top of native widgets, intercepting mouse clicks.
    # Separate the same brand/chips into columns without changing their CSS classes.
    cols = st.columns([2.35, 0.88, 1.15, 0.95, 1.45, 1.65, 0.85],
                      vertical_alignment="center", gap="small")
    c_brand, c_date, c_clock, c_alerts, c_vessel, c_mode, c_refresh = cols

    with c_brand:
        st.html(C.head_brand_html())
    with c_date:
        st.html(C.header_chip("calendar", C.esc(today)))
    with c_clock:
        st.html(C.header_chip("clock", f'{C.esc(clock)} <span class="bc-dim">(GMT+6)</span>'))
    with c_alerts:
        tone = "bad" if alerts_count else "ok"
        st.html(C.header_chip("alert", f'Alerts ({alerts_count})', tone,
                              "Critical and warning alerts in the last 24 hours"))

    with c_vessel:
        names = [ALL]
        if vdf is not None and not vdf.empty and "vessel_name" in vdf.columns:
            names += sorted(vdf["vessel_name"].dropna().astype(str).unique().tolist())
        if st.session_state.get("vessel", ALL) not in names:
            st.session_state["vessel"] = ALL
        st.selectbox("Vessel", names, key="vessel", label_visibility="collapsed",
                     help="Filter vessel positions and voyage details.")

    with c_mode:
        st.radio("Display mode", theme.MODES, horizontal=True, key="mode",
                 label_visibility="collapsed", help="Switch the dashboard between Default, Dark, and Light.")

    def refresh_dashboard() -> None:
        # Callback runs before Streamlit's automatic rerun, so the rerun uses fresh query data.
        st.cache_data.clear()

    with c_refresh:
        st.button("Refresh", key="refresh_dashboard", on_click=refresh_dashboard,
                  width="stretch", help="Clear cached data and reload the dashboard.")


def footer() -> None:
    note = st.secrets.get("FOOTER_NOTE", "Data source: simulated BOGCL operations feed on Databricks. All times are GMT+6.")
    st.html(f'<div class="bc bc-foot">{C.esc(note)}</div>')


# --------------------------------------------------------------------------- shared panels
def route_map_panel(vdf: pd.DataFrame, selected: str | None, height: int = 360) -> None:
    ports, routes = load(data.ports), load(data.routes)
    trk = None
    if selected:
        vid = vdf[vdf.vessel_name == selected].iloc[0].voyage_id
        trk = load(data.track, vid) if isinstance(vid, str) else None
    with st.container(key="mapcard"):
        title = f"Vessel route: {selected}" if selected else "Fleet operations: vessel positions"
        st.html(f'<div class="bc bc-ph" style="margin:0"><span>{C.esc(title)}</span></div>')
        st.iframe(map_view.build_map_html(vdf, ports, routes, selected, trk, st.session_state.get("mode", "Default"), height),
                  height=height + 4)
        st.html(C.voyage_strip(vdf, selected))


# --------------------------------------------------------------------------- pages
def overview_page() -> None:
    vdf = load(data.vessels)
    if vdf is None or vdf.empty:
        st.html(C.note("No vessel data yet. Check that the Databricks gold views exist and the simulator has run.", "warn"))
        return
    selected = selected_vessel()

    left, right = st.columns([1.55, 1], gap="small")
    with left:
        route_map_panel(vdf, selected)
    with right:
        st.html(C.fleet_ops_card(vdf, selected))

    berths, bays, ta = load(data.berths), load(data.bays), load(data.turnaround)
    ops, today, status, tanks = load(data.active_ops), load(data.cargo_today), load(data.system_status), load(data.tanks)
    today_mt = None if today is None or today.empty else today.iloc[0].cargo_today_mt
    sys_status = "Normal" if status is None or status.empty else status.iloc[0].system_status
    st.html('<div class="bc bc-cq"><div class="bc-grid bc-r3">' + C.terminal_card(berths, bays, ta)
            + C.cargo_card(ops, tanks, today_mt, sys_status, selected) + "</div></div>")

    k, al, head = load(data.kpis), load(data.alerts, 25), load(data.header)
    clock = "" if head is None or head.empty else head.iloc[0].clock
    st.html('<div class="bc bc-cq"><div class="bc-grid bc-r4">' + C.exec_kpi_card(k, clock) + C.trend_card(k, st.session_state.get("mode", "Default")) + C.alerts_card(al) + "</div></div>")
    footer()


def fleet_page() -> None:
    vdf = load(data.vessels)
    if vdf is None or vdf.empty:
        st.html(C.note("No vessel data yet.", "warn"))
        return
    selected = selected_vessel()
    route_map_panel(vdf, selected, height=440)
    a, b = st.columns([2.2, 1], gap="small")
    with a:
        st.html(C.fleet_table_card(vdf, selected))
    with b:
        st.html(C.queue_card(vdf))
    footer()


def terminal_page() -> None:
    berths, bays, ta, vdf = load(data.berths), load(data.bays), load(data.turnaround), load(data.vessels)
    a, b = st.columns([1.35, 1], gap="small")
    with a:
        st.html(C.terminal_card(berths, bays, ta, compact=False))
    with b:
        if vdf is not None and not vdf.empty:
            st.html(C.queue_card(vdf))
    footer()


def cargo_page() -> None:
    ops, tanks, today, status = load(data.active_ops), load(data.tanks), load(data.cargo_today), load(data.system_status)
    today_mt = None if today is None or today.empty else today.iloc[0].cargo_today_mt
    sys_status = "Normal" if status is None or status.empty else status.iloc[0].system_status
    st.html(C.cargo_card(ops, tanks, today_mt, sys_status, selected_vessel()))
    if tanks is not None and not tanks.empty:
        st.html(C.tank_table_card(tanks))
    footer()


def alerts_page() -> None:
    counts, al = load(data.alert_counts), load(data.alerts, 150)
    if counts is not None and not counts.empty:
        c = counts.iloc[0]
        st.html(C.count_tiles([("Critical, last 24 h", str(int(c.critical_24h)), "needs action"),
                               ("Warnings, last 24 h", str(int(c.warning_24h)), "watch"),
                               ("Information, last 24 h", str(int(c.info_24h)), "events")]))
    st.html(C.alerts_table_card(al))
    footer()


# --------------------------------------------------------------------------- AI assistant
def render_entry(entry: dict) -> None:
    with st.chat_message(entry["role"]):
        if entry.get("error"):
            st.html(C.note(entry["error"], "bad"))
        for t in entry.get("text") or []:
            st.markdown(t)
        if entry.get("sql_description"):
            st.html(f'<div class="bc bc-foot">{C.esc(entry["sql_description"])}</div>')
        df = entry.get("df")
        if df is not None and not df.empty:
            st.html(C.df_table(df))
        elif entry.get("sql") and df is not None:
            st.html(C.note("The query returned no rows."))
        if entry.get("sql"):
            st.html(C.sql_details(entry["sql"]))


def assistant_page() -> None:
    st.html('<div class="bc bc-card"><div class="bc-ph"><span>BOGCL AI assistant</span></div>'
            '<div style="font-size:15px;line-height:1.5">Ask about vessels, voyages, berths, tanks, cargo operations, delays, alerts and KPIs. '
            'Every answer comes from the operations data and shows the SQL behind it.</div></div>')
    ss = st.session_state
    ss.setdefault("chat", [])
    ss.setdefault("conversation_id", None)
    ss.setdefault("question_count", 0)

    if not ss.chat and "pending" not in ss:
        cols = st.columns(3)
        for i, qn in enumerate(EXAMPLE_QUESTIONS):
            if cols[i % 3].button(qn, key=f"ex{i}", width="stretch"):
                ss["pending"] = qn
                st.rerun()

    for entry in ss.chat:
        render_entry(entry)
    if ss.chat and st.button("Start a new conversation"):
        ss.chat, ss.conversation_id = [], None
        st.rerun()

    typed = st.chat_input("Ask a question about BOGCL operations", max_chars=MAX_QUESTION_CHARS)
    prompt = ss.pop("pending", None) or typed
    if not prompt:
        return
    if ss.question_count >= MAX_QUESTIONS_PER_SESSION:
        st.html(C.note(f"This session reached the limit of {MAX_QUESTIONS_PER_SESSION} questions. Refresh the page to start again.", "warn"))
        return
    ss.question_count += 1
    user_entry = {"role": "user", "text": [prompt]}
    ss.chat.append(user_entry)
    render_entry(user_entry)
    with st.chat_message("assistant"):
        with st.spinner("Analysing the data..."):
            result = genie_client.ask(prompt, ss.conversation_id)
    ss.conversation_id = result["conversation_id"] or ss.conversation_id
    entry = {"role": "assistant", **result}
    ss.chat.append(entry)
    render_entry(entry)
