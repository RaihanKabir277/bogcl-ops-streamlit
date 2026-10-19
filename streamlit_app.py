"""BOGCL Marine Operations: public Streamlit front-end for the Databricks operations data and Genie space.

Run locally:   streamlit run streamlit_app.py
Secrets:       .streamlit/secrets.toml (local) or the Secrets box in Streamlit Community Cloud
"""
from __future__ import annotations

import streamlit as st

import data
import views

st.set_page_config(page_title="BOGCL Marine Operations", page_icon=":ship:", layout="wide",
                   initial_sidebar_state="expanded")

# The colour mode lives in session state (set by the radio in the top bar), so it is known before the page is drawn.
views.inject_css(st.session_state.get("mode", "Default"))
views.check_secrets()
views.password_gate()

views.header(views.load(data.vessels))


from pathlib import Path

# Zylo company branding in the sidebar
logo_path = Path(__file__).parent / "assets" / "zylo_logo.jpeg"

if logo_path.exists():
    with st.sidebar:
        st.image(str(logo_path), width=140)
        st.caption("Developed by Zylo")
        st.divider()


pages = [
    st.Page(views.overview_page, title="Overview", icon=":material/dashboard:", url_path="overview", default=True),
    st.Page(views.fleet_page, title="Fleet Operations", icon=":material/directions_boat:", url_path="fleet"),
    st.Page(views.terminal_page, title="Terminal Operations", icon=":material/anchor:", url_path="terminal"),
    st.Page(views.cargo_page, title="Cargo Operations", icon=":material/propane_tank:", url_path="cargo"),
    st.Page(views.alerts_page, title="Alerts", icon=":material/notifications:", url_path="alerts"),
    st.Page(views.assistant_page, title="AI Assistant", icon=":material/smart_toy:", url_path="assistant"),
]
current = st.navigation(pages, position="sidebar")
current.run()
