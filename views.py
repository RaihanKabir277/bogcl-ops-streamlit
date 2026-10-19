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
