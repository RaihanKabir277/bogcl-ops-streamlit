"""Pages and layout for the BOGCL dashboard."""
from __future__ import annotations

import hmac
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
import base64
from pathlib import Path
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
@st.fragment(run_every="1s")
def _live_date_chip() -> None:
    """Render the actual Bangladesh calendar date, refreshed independently each second."""
    now = datetime.now(ZoneInfo("Asia/Dhaka"))
    today = now.strftime("%d %b %Y").lstrip("0")
    st.html(C.header_chip("calendar", C.esc(today)))


@st.fragment(run_every="1s")
def _live_clock_chip() -> None:
    """Render the actual Bangladesh wall clock, ticking without a full-page rerun."""
    now = datetime.now(ZoneInfo("Asia/Dhaka"))
    clock = now.strftime("%I:%M %p").lstrip("0")
    st.html(C.header_chip("clock", f'{C.esc(clock)} <span class="bc-dim">(GMT+6)</span>'))


def _header_responsive_css() -> None:
    st.html("""<style>
      [data-testid="stRadio"] [role="radiogroup"] {
        display:flex; flex-wrap:nowrap !important; align-items:center; gap:clamp(3px, .5vw, 8px);
      }
      [data-testid="stRadio"] label { white-space:nowrap !important; min-width:max-content; }
      [data-testid="stSelectbox"], [data-testid="stButton"] { position:relative; z-index:2; min-width:0; }
      .st-key-refresh_dashboard button { white-space:nowrap; }
    </style>""")


def header(vdf: pd.DataFrame | None) -> None:
    _header_responsive_css()
    head = load(data.header)
    if head is not None and not head.empty:
        alerts_count = int(head.iloc[0].open_alerts)
    else:
        alerts_count = 0

    # Keep the original brand/chip styling, but split information and controls into
    # two rows. The old single row squeezed the radio labels into vertical letters
    # and allowed the wide brand HTML to overlap the widgets at full-screen widths.
    info_cols = st.columns([2.45, 0.9, 1.15, 1.0],
                           vertical_alignment="center", gap="small")
    c_brand, c_date, c_clock, c_alerts = info_cols
    with c_brand:
        st.html(C.head_brand_html())
    with c_date:
        _live_date_chip()
    with c_clock:
        _live_clock_chip()
    with c_alerts:
        tone = "bad" if alerts_count else "ok"
        st.html(C.header_chip("alert", f'Alerts ({alerts_count})', tone,
                              "Critical and warning alerts in the last 24 hours"))

    control_cols = st.columns([1.45, 2.0, 0.8],
                              vertical_alignment="center", gap="small")
    c_vessel, c_mode, c_refresh = control_cols
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
        # Clearing the cache in the callback makes the following automatic rerun fresh.
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
    st.html('<div class="bc bc-cq"><div class="bc-grid bc-r4">' + C.exec_kpi_card(k, clock) + C.executive_fleet_insight_card(vdf) + C.alerts_card(al) + "</div></div>")
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


# --------------------------------------------------------------------------- AI assistant watermark
def add_ai_watermark() -> None:
    """Add a low-contrast watermark behind the AI Assistant page."""
    image_path = (
        Path(__file__).parent
        / "assets"
        / "bogcl_ai_watermark.png"
    )

    if not image_path.exists():
        return

    encoded = base64.b64encode(
        image_path.read_bytes()
    ).decode("ascii")

    mode = st.session_state.get("mode", "Default")

    # Match the overlay to the selected dashboard theme.
    if mode == "Dark":
        overlay = "rgba(7, 17, 31, 0.76)"
        chat_bg = "rgba(12, 25, 42, 0.94)"
    else:
        overlay = "rgba(245, 250, 255, 0.45)"
        chat_bg = "rgba(255, 255, 255, 0.91)"

    st.html(f"""
    <div class="bogcl-ai-watermark-sentinel"
         style="display:none"></div>

    <style>
    [data-testid="stMainBlockContainer"]:has(
        .bogcl-ai-watermark-sentinel
    ) {{
        background-image:
            linear-gradient(
                {overlay},
                {overlay}
            ),
            url("data:image/png;base64,{encoded}") !important;
        background-position: center center;
        background-size: cover;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}

    [data-testid="stChatMessage"] {{
        background: {chat_bg};
        border: 1px solid rgba(110, 145, 175, 0.18);
        border-radius: 14px;
        padding: 12px 16px;
    }}
    </style>
    """)


def assistant_page() -> None:
    """Responsive AI assistant page with mode-aware BOGCL branding."""
    add_ai_watermark()
    import base64
    from pathlib import Path

    # Embed the supplied artwork so the page works reliably on Streamlit Cloud.
    _art_path = Path(__file__).with_name("assets") / "bogcl_ai.png"
    try:
        _art = base64.b64encode(_art_path.read_bytes()).decode("ascii")
    except OSError:
        _art = ""
    _art_uri = f"data:image/png;base64,{_art}" if _art else ""

    st.html(f"""
    <style>
      .st-key-assistant_page {{
        position: relative;
        isolation: isolate;
        min-height: 72vh;
        padding: clamp(12px, 2.2vw, 28px) clamp(8px, 1.6vw, 20px) 24px;
        border-radius: 22px;
        overflow: hidden;
        background: transparent;
      }}
      .st-key-assistant_page::before {{
        content: "";
        position: absolute;
        z-index: -1;
        pointer-events: none;
        inset: 0;
        background-image: url("__ART_URI__");
        background-repeat: no-repeat;
        background-position: center 230px;
        background-size: min(74vw, 780px) auto;
        opacity: .055;
        filter: saturate(.8);
      }}
      .bc-ai-hero {{
        text-align: center;
        max-width: 900px;
        margin: 0 auto 22px;
        padding: 4px 12px 16px;
      }}
      .bc-ai-hero img {{
        display: block;
        width: min(100%, 370px);
        height: auto;
        margin: 0 auto 14px;
        border-radius: 12px;
        filter: drop-shadow(0 8px 20px rgba(10,55,100,.12));
      }}
      .bc-ai-eyebrow {{
        color: var(--accent);
        text-transform: uppercase;
        letter-spacing: .14em;
        font-size: 11px;
        font-weight: 800;
        margin-bottom: 7px;
      }}
      .bc-ai-title {{
        color: var(--text);
        font-size: clamp(25px, 3vw, 36px);
        font-weight: 850;
        line-height: 1.14;
        margin: 0 0 10px;
      }}
      .bc-ai-description {{
        color: var(--muted);
        font-size: clamp(14px, 1.25vw, 16px);
        line-height: 1.65;
        max-width: 760px;
        margin: 0 auto;
      }}
      .bc-ai-section-label {{
        color: var(--muted);
        font-size: 11px;
        font-weight: 800;
        letter-spacing: .1em;
        text-transform: uppercase;
        margin: 4px 0 10px;
      }}
      .st-key-assistant_page [data-testid="stChatMessage"] {{
        max-width: 100%;
        backdrop-filter: blur(10px);
        box-shadow: 0 5px 20px rgba(5,30,60,.06);
        padding: 14px 16px;
      }}
      .st-key-assistant_page .stButton > button {{
        white-space: normal;
        min-height: 48px;
        height: auto;
        text-align: left;
        line-height: 1.35;
        padding: 10px 13px;
        background: var(--card) !important;
        border-color: var(--border) !important;
        box-shadow: 0 3px 12px rgba(5,30,60,.045);
        transition: border-color .16s ease, transform .16s ease, box-shadow .16s ease;
      }}
      .st-key-assistant_page .stButton > button:hover {{
        transform: translateY(-1px);
        border-color: var(--accent) !important;
        box-shadow: 0 7px 18px rgba(5,30,60,.09);
      }}
      .st-key-assistant_page [data-testid="stChatInput"] {{ max-width: 100%; }}
      @media (max-width: 700px) {{
        .st-key-assistant_page {{ padding: 8px 2px 18px; border-radius: 14px; }}
        .st-key-assistant_page::before {{
          background-position: center 190px;
          background-size: 115vw auto;
          opacity: .04;
        }}
        .bc-ai-hero {{ margin-bottom: 14px; padding-bottom: 8px; }}
        .bc-ai-hero img {{ width: min(88%, 300px); margin-bottom: 10px; }}
      }}
    </style>
    """.replace("__ART_URI__", _art_uri))

    ss = st.session_state
    ss.setdefault("chat", [])
    ss.setdefault("conversation_id", None)
    ss.setdefault("question_count", 0)

    with st.container(key="assistant_page"):
        st.html(f"""
        <section class="bc-ai-hero">
          <div class="bc-ai-eyebrow">Marine operations intelligence</div>
          <h1 class="bc-ai-title">BOGCL AI Assistant</h1>
          <p class="bc-ai-description">This Agent provides real-time and historical insights into marine operations, including vessel movements, cargo handling, berth and bay status, and operational performance across ports.</p>
        </section>
        """)

        if not ss.chat and "pending" not in ss:
            st.html('<div class="bc-ai-section-label">Suggested questions</div>')
            cols = st.columns(3, gap="small")
            for i, qn in enumerate(EXAMPLE_QUESTIONS):
                if cols[i % 3].button(qn, key=f"ex{i}", width="stretch"):
                    ss["pending"] = qn
                    st.rerun()

        for entry in ss.chat:
            render_entry(entry)

        if ss.chat and st.button("Start a new conversation", key="assistant_new_chat"):
            ss.chat, ss.conversation_id = [], None
            st.rerun()

        typed = st.chat_input("Ask about vessels, voyages, cargo, berths, delays or alerts…",
                              max_chars=MAX_QUESTION_CHARS)
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
            with st.spinner("Analysing marine operations…"):
                result = genie_client.ask(prompt, ss.conversation_id)
        ss.conversation_id = result["conversation_id"] or ss.conversation_id
        entry = {"role": "assistant", **result}
        ss.chat.append(entry)
        render_entry(entry)
