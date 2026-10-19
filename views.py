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
