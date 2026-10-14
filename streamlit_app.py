"""BOGCL Operations: public Streamlit front-end for the Databricks marine operations data and Genie space.

Run locally:   streamlit run streamlit_app.py
Secrets:       .streamlit/secrets.toml (local) or the Secrets box in Streamlit Community Cloud
"""
from __future__ import annotations

import hmac

import altair as alt
import pandas as pd
import pydeck as pdk
import streamlit as st

import data
import genie_client

st.set_page_config(page_title="BOGCL Operations", page_icon=":ship:", layout="wide")

REQUIRED_SECRETS = ["DATABRICKS_HOST", "DATABRICKS_TOKEN", "DATABRICKS_WAREHOUSE_ID", "GENIE_SPACE_ID"]
MAX_QUESTIONS_PER_SESSION = 20
MAX_QUESTION_CHARS = 600

# One colour per vessel status. The legend uses Streamlit's named colours that match these RGB values.
STATUS_RGB = {"En Route": [0, 104, 201], "At Anchor": [255, 135, 0], "At Port": [9, 171, 59]}
STATUS_LEGEND = {"En Route": ":blue[●] En Route", "At Anchor": ":orange[●] At Anchor", "At Port": ":green[●] At Port"}
BAND_COLORS = {"Normal": "#0E7C86", "High (90%+)": "#E3A008", "Critical (95%+)": "#C8372D", "Low (15% or less)": "#6B7C93"}

EXAMPLE_QUESTIONS = [
    "Which vessels are expected to arrive in the next 48 hours?",
    "Which berths are free right now?",
    "Which tanks are above 90% full?",
    "Show delays by cause for the last 7 days",
    "What are the critical alerts from the last 24 hours?",
    "How much cargo has been transferred today?",
]


# --------------------------------------------------------------------------- guards
def check_secrets() -> None:
    try:
        missing = [k for k in REQUIRED_SECRETS if k not in st.secrets]
    except Exception:
        missing = REQUIRED_SECRETS
    if missing:
        st.error("This app is not configured yet. Missing secrets: " + ", ".join(missing))
        st.info("Add them under App settings > Secrets (Streamlit Cloud) or in .streamlit/secrets.toml (local).")
        st.stop()


def password_gate() -> None:
    """Optional. Set APP_PASSWORD in secrets to put a password in front of the app."""
    expected = st.secrets.get("APP_PASSWORD", "")
    if not expected or st.session_state.get("authed"):
        return
    st.title("BOGCL Operations")
    pw = st.text_input("Password", type="password")
    if pw:
        if hmac.compare_digest(pw.encode(), expected.encode()):
            st.session_state["authed"] = True
            st.rerun()
        st.error("Wrong password.")
    st.stop()


def load(fn, *args):
    """Run one data query. A failing widget shows a short error instead of crashing the whole page."""
    try:
        return fn(*args)
    except Exception as exc:
        st.error(f"Could not load {fn.__name__}: {exc}")
        return None


# --------------------------------------------------------------------------- small helpers
def n0(x) -> str:
    return "–" if x is None or pd.isna(x) else f"{x:,.0f}"


def n1(x) -> str:
    return "–" if x is None or pd.isna(x) else f"{x:,.1f}"


def tank_band(level: float) -> str:
    if level >= 95:
        return "Critical (95%+)"
    if level >= 90:
        return "High (90%+)"
    if level <= 15:
        return "Low (15% or less)"
    return "Normal"


def style_severity(df: pd.DataFrame):
    colors = {"Critical": "#f8d7da", "Warning": "#fff3cd", "Info": "#e7f1ff"}
    fn = lambda v: f"background-color: {colors.get(v, '')}; color: #1b1b1b"
    styler = df.style
    return styler.map(fn, subset=["severity"]) if hasattr(styler, "map") else styler.applymap(fn, subset=["severity"])


# --------------------------------------------------------------------------- map
def build_map(vdf: pd.DataFrame, selected: str | None) -> pdk.Deck:
    ports = load(data.ports)
    routes = load(data.routes)
    layers, points = [], []

    def route_paths(frame: pd.DataFrame):
        return [{"path": g[["lon", "lat"]].values.tolist(), "name": rid} for rid, g in frame.groupby("route_id")]

    if selected:
        v = vdf[vdf.vessel_name == selected].iloc[0]
        if routes is not None and not routes.empty:
            same = routes[((routes.origin_port == v.origin_port) & (routes.dest_port == v.dest_port))
                          | ((routes.origin_port == v.dest_port) & (routes.dest_port == v.origin_port))]
            if not same.empty:
                paths = route_paths(same)
                layers.append(pdk.Layer("PathLayer", paths, get_path="path", get_color=[150, 160, 175],
                                        width_min_pixels=3, pickable=False))
                points += [p for path in paths for p in path["path"]]
        trk = load(data.track, v.voyage_id) if isinstance(v.voyage_id, str) else None
        if trk is not None and len(trk) > 1:
            layers.append(pdk.Layer("PathLayer", [{"path": trk[["lon", "lat"]].values.tolist(), "name": "Track"}],
                                    get_path="path", get_color=[0, 104, 201], width_min_pixels=3))
        if ports is not None:
            ends = ports[ports.port_id.isin([v.origin_port, v.dest_port])].assign(
                label=lambda d: d.port_name + " (" + d.port_role + ")",
                color=lambda d: d.port_role.map(lambda r: [9, 171, 59] if r == "Origin" else [200, 55, 45]))
            layers.append(pdk.Layer("ScatterplotLayer", ends.to_dict("records"), get_position=["lon", "lat"],
                                    get_fill_color="color", get_radius=9, radius_units="pixels", pickable=True))
            points += ends[["lon", "lat"]].values.tolist()
        pos = vdf[vdf.vessel_name == selected].assign(
            color=lambda d: d.status.map(lambda s: STATUS_RGB.get(s, [90, 90, 90])),
            label=lambda d: d.vessel_name + " - " + d.status + " at " + d.speed_kn.round(1).astype(str) + " kn")
    else:
        if routes is not None and not routes.empty:
            paths = route_paths(routes)
            layers.append(pdk.Layer("PathLayer", paths, get_path="path", get_color=[190, 196, 205],
                                    width_min_pixels=2, pickable=False))
            points += [p for path in paths for p in path["path"]]
        if ports is not None:
            layers.append(pdk.Layer(
                "ScatterplotLayer",
                ports.assign(label=ports.port_name).to_dict("records"),
                get_position=["lon", "lat"], get_fill_color=[110, 120, 135], get_radius=5, radius_units="pixels",
                pickable=True))
        pos = vdf.assign(
            color=lambda d: d.status.map(lambda s: STATUS_RGB.get(s, [90, 90, 90])),
            label=lambda d: d.vessel_name + " - " + d.status + " at " + d.speed_kn.round(1).astype(str) + " kn")

    layers.append(pdk.Layer("ScatterplotLayer", pos[["lon", "lat", "color", "label"]].to_dict("records"),
                            get_position=["lon", "lat"], get_fill_color="color", get_radius=8, radius_units="pixels",
                            stroked=True, get_line_color=[255, 255, 255], line_width_min_pixels=1, pickable=True))
    points += pos[["lon", "lat"]].values.tolist()
    view = pdk.data_utils.compute_view(points, view_proportion=0.9) if points else pdk.ViewState(latitude=15, longitude=75, zoom=3)
    return pdk.Deck(layers=layers, initial_view_state=view, map_style=None, tooltip={"text": "{label}"})


# --------------------------------------------------------------------------- dashboard sections
def section_vessel_information(vdf: pd.DataFrame, selected: str | None) -> None:
    st.subheader("Vessel information")
    if selected:
        r = vdf[vdf.vessel_name == selected].iloc[0]
        a, b = st.columns(2)
        a.metric("Cargo (MT)", n0(r.cargo_mt), border=True)
        b.metric("Voyage progress", f"{n0(r.pct_covered)}%", border=True)
        a, b = st.columns(2)
        a.metric("Average speed (knots)", n1(r.avg_speed_kn), border=True)
        b.metric("Distance covered (NM)", f"{n0(r.distance_covered_nm)} of {n0(r.distance_nm)}", border=True)
        a, b = st.columns(2)
        a.metric("Status", f"{r.status}", help=str(r.activity), border=True)
        slip = None if pd.isna(r.eta_slip_hrs) else f"{r.eta_slip_hrs:+.1f} h vs plan"
        b.metric("ETA (GMT+6)", r.eta_local if isinstance(r.eta_local, str) else "–", slip,
                 delta_color="inverse", border=True)
        st.caption(f"{r.vessel_type}, {r.voyage_type.lower() if isinstance(r.voyage_type, str) else ''} voyage "
                   f"{r.from_port} to {r.to_port}" + (f", carrying {r['product']}" if isinstance(r["product"], str) else ""))
        return
    laden = vdf[vdf.voyage_type == "Laden"]
    en_route = vdf[vdf.status == "En Route"]
    covered, total = en_route.distance_covered_nm.sum(), en_route.distance_nm.sum()
    a, b = st.columns(2)
    a.metric("Cargo on laden voyages (MT)", n0(laden.cargo_mt.sum()), border=True)
    b.metric("Progress of en-route voyages", f"{(100 * covered / total) if total else 0:.1f}%", border=True)
    a, b = st.columns(2)
    a.metric("Average speed, under way (knots)", n1(en_route.speed_kn.mean()), border=True)
    b.metric("Distance covered, en-route (NM)", n0(covered), border=True)
    st.metric("Fleet", f"{len(vdf)} vessels", border=True)


def section_active_vessels(vdf: pd.DataFrame) -> None:
    st.subheader("Active vessels")
    order = {"En Route": 0, "At Anchor": 1, "At Port": 2}
    tbl = (vdf.assign(_o=vdf.status.map(order).fillna(9)).sort_values(["_o", "hours_to_arrival"])
           [["vessel_name", "status", "from_port", "to_port", "product", "eta_local", "speed_kn"]]
           .rename(columns={"vessel_name": "Vessel", "status": "Status", "from_port": "From", "to_port": "To",
                            "product": "Cargo", "eta_local": "ETA (GMT+6)", "speed_kn": "Speed (kn)"}))
    st.dataframe(tbl, hide_index=True, height=300, column_config={"Speed (kn)": st.column_config.NumberColumn(format="%.1f")})


def section_counters(vdf: pd.DataFrame) -> None:
    counts = vdf.status.value_counts()
    a, b = st.columns(2)
    a.metric("Live vessels", len(vdf), border=True)
    b.metric("En route", int(counts.get("En Route", 0)), border=True)
    a, b = st.columns(2)
    a.metric("At anchor", int(counts.get("At Anchor", 0)), border=True)
    b.metric("At port", int(counts.get("At Port", 0)), border=True)


def section_terminal_cargo() -> None:
    berths, bays, ops, today = load(data.berths), load(data.bays), load(data.active_ops), load(data.cargo_today)
    st.subheader("Terminal and cargo")
    cols = st.columns(4)
    if berths is not None and not berths.empty:
        occ = int((berths.status == "Occupied").sum())
        cols[0].metric("Berth occupancy", f"{100 * occ / len(berths):.0f}%", f"{occ} of {len(berths)} berths", delta_color="off", border=True)
    if bays is not None and not bays.empty:
        b = bays.iloc[0]
        cols[1].metric("Loading bay utilisation", f"{100 * b.busy / b.total:.0f}%", f"{int(b.busy)} of {int(b.total)} bays loading",
                       delta_color="off", border=True)
    if ops is not None:
        dis = ops[ops.op_type == "Discharge"]
        planned = dis.planned_mt.sum()
        cols[2].metric("Discharge progress", f"{(100 * dis.transferred_mt.sum() / planned) if planned else 0:.0f}%",
                       f"{len(dis)} operations in progress", delta_color="off", border=True)
    if today is not None and not today.empty:
        cols[3].metric("Cargo transferred today (MT)", n0(today.iloc[0].cargo_today_mt), border=True)

    left, right = st.columns([3, 2])
    with left:
        st.markdown("**Active cargo operations**")
        if ops is not None:
            if ops.empty:
                st.info("No cargo operation is running right now.")
            else:
                st.dataframe(
                    ops[["vessel_name", "op_type", "product", "berth_id", "tank_id", "progress_pct", "planned_mt",
                         "flow_rate_klph", "est_completion", "status"]]
                    .rename(columns={"vessel_name": "Vessel", "op_type": "Operation", "product": "Product", "berth_id": "Berth",
                                     "tank_id": "Tank", "progress_pct": "Progress", "planned_mt": "Planned (MT)",
                                     "flow_rate_klph": "Flow (KL/h)", "est_completion": "Est. completion (GMT+6)",
                                     "status": "Status"}),
                    hide_index=True, height=280,
                    column_config={"Progress": st.column_config.ProgressColumn(format="%.0f%%", min_value=0, max_value=100),
                                   "Planned (MT)": st.column_config.NumberColumn(format="%,.0f"),
                                   "Flow (KL/h)": st.column_config.NumberColumn(format="%,.0f")})
    with right:
        st.markdown("**Berth status**")
        if berths is not None:
            st.dataframe(
                berths[["berth_name", "port_name", "status", "vessel_name", "occupied_since", "discharge_pct"]]
                .rename(columns={"berth_name": "Berth", "port_name": "Port", "status": "Status", "vessel_name": "Vessel",
                                 "occupied_since": "Since (GMT+6)", "discharge_pct": "Discharged"}),
                hide_index=True, height=280,
                column_config={"Discharged": st.column_config.ProgressColumn(format="%.0f%%", min_value=0, max_value=100)})


def section_kpis() -> pd.DataFrame | None:
    k = load(data.kpis)
    st.subheader("KPIs today")
    if k is None or k.empty:
        return k
    live = k[k.is_live == True]  # noqa: E712
    today = (live if not live.empty else k).iloc[-1]
    prev = k[k.kpi_date < today.kpi_date]
    y = prev.iloc[-1] if not prev.empty else None

    def delta(col, fmt="{:+,.1f}"):
        return None if y is None else fmt.format(today[col] - y[col])

    items = [
        ("Fleet utilisation", f"{today.fleet_utilization_pct:.1f}%", delta("fleet_utilization_pct"), "normal"),
        ("Cargo delivered (MT)", n0(today.cargo_delivered_mt), delta("cargo_delivered_mt", "{:+,.0f}"), "normal"),
        ("On-time delivery", f"{today.on_time_pct:.1f}%", delta("on_time_pct"), "normal"),
        ("Operational delay (hours)", f"{today.operational_delay_hrs:.1f}", delta("operational_delay_hrs"), "inverse"),
        ("Fuel consumption (KL)", n1(today.fuel_consumption_kl), delta("fuel_consumption_kl"), "inverse"),
        ("Critical alerts", f"{int(today.critical_alerts)}", delta("critical_alerts", "{:+,.0f}"), "inverse"),
    ]
    cols = st.columns(6)
    for col, (label, value, d, color) in zip(cols, items):
        col.metric(label, value, d, delta_color=color, border=True)
    st.caption(f"Today is {today.kpi_date} and is a partial day, so cargo, fuel, delay and alert totals compare against a full "
               f"previous day. Arrows show the change versus yesterday.")
    return k


def section_charts(k: pd.DataFrame | None) -> None:
    left, right = st.columns(2)
    with left:
        st.markdown("**Seven-day KPI trend**")
        if k is not None and not k.empty:
            lines = k.rename(columns={"fleet_utilization_pct": "Fleet utilisation %", "on_time_pct": "On-time delivery %"}).melt(
                id_vars="kpi_date", value_vars=["Fleet utilisation %", "On-time delivery %"], var_name="KPI", value_name="value")
            base_x = alt.X("kpi_date:N", title=None, sort=None)
            bars = alt.Chart(k).mark_bar(opacity=0.35, color="#6B7C93").encode(
                x=base_x, y=alt.Y("operational_delay_hrs:Q", title="Operational delay (hours)", axis=alt.Axis(orient="right")),
                tooltip=["kpi_date", alt.Tooltip("operational_delay_hrs:Q", title="Delay (h)")])
            ln = alt.Chart(lines).mark_line(point=True).encode(
                x=base_x, y=alt.Y("value:Q", title="Percent", scale=alt.Scale(domain=[0, 100])),
                color=alt.Color("KPI:N", legend=alt.Legend(orient="bottom", title=None)),
                tooltip=["kpi_date", "KPI", alt.Tooltip("value:Q", format=".1f")])
            st.altair_chart(alt.layer(bars, ln).resolve_scale(y="independent").properties(height=320), width="stretch")
    with right:
        st.markdown("**Tank levels**")
        t = load(data.tanks)
        if t is not None and not t.empty:
            t = t.assign(band=t.level_pct.map(tank_band))
            bars = alt.Chart(t).mark_bar().encode(
                x=alt.X("tank_id:N", title=None, sort=None),
                y=alt.Y("level_pct:Q", title="Level (%)", scale=alt.Scale(domain=[0, 100])),
                color=alt.Color("band:N", title=None, legend=alt.Legend(orient="bottom"),
                                scale=alt.Scale(domain=list(BAND_COLORS), range=list(BAND_COLORS.values()))),
                tooltip=["tank_id", "product", "port_id", alt.Tooltip("level_pct:Q", format=".1f", title="Level %"),
                         alt.Tooltip("volume_kl:Q", format=",.0f", title="Volume (KL)"),
                         alt.Tooltip("temperature_c:Q", format=".1f", title="Temp (°C)")])
            rule = alt.Chart(pd.DataFrame({"y": [90]})).mark_rule(strokeDash=[4, 4], color="#C8372D").encode(y="y:Q")
            st.altair_chart((bars + rule).properties(height=320), width="stretch")


def section_insights(vdf: pd.DataFrame) -> None:
    st.subheader("Fleet insights")
    er = vdf[(vdf.status == "En Route") & vdf.avg_speed_kn.notna()]
    if len(er) < 2:
        st.info("Not enough vessels under way to compare speeds.")
        return
    avg = er.avg_speed_kn.mean()
    best, worst = er.loc[er.avg_speed_kn.idxmax()], er.loc[er.avg_speed_kn.idxmin()]
    a, b, c = st.columns(3)
    with a.container(border=True):
        st.markdown("**Fastest voyage average**")
        st.write(f"{best.vessel_name}: {best.avg_speed_kn:.1f} kn, {100 * (best.avg_speed_kn / avg - 1):+.1f}% vs fleet average")
    with b.container(border=True):
        st.markdown("**Slowest voyage average**")
        gap = 100 * (worst.avg_speed_kn / avg - 1)
        st.write(f"{worst.vessel_name}: {worst.avg_speed_kn:.1f} kn, {gap:+.1f}% vs fleet average")
        if gap <= -10:
            st.warning("More than 10% below the fleet average.")
    with c.container(border=True):
        st.markdown("**Fleet statistics**")
        st.write(f"Average {avg:.1f} kn across {len(er)} vessels under way. "
                 f"Range {er.avg_speed_kn.min():.1f} to {er.avg_speed_kn.max():.1f} kn.")


def section_alerts() -> None:
    st.subheader("Latest alerts")
    counts, al = load(data.alert_counts), load(data.alerts)
    if counts is not None and not counts.empty:
        c = counts.iloc[0]
        a, b = st.columns(2)
        a.metric("Critical alerts, last 24 hours", int(c.critical_24h), border=True)
        b.metric("Warnings, last 24 hours", int(c.warning_24h), border=True)
    if al is not None:
        shown = al.rename(columns={"time_dhaka": "Time (GMT+6)", "alert_id": "Alert", "severity": "severity",
                                   "alert_type": "Type", "asset_name": "Asset", "message": "Message"})
        st.dataframe(style_severity(shown), hide_index=True, height=360)


# --------------------------------------------------------------------------- tabs
def dashboard_tab() -> None:
    vdf = load(data.vessels)
    if vdf is None or vdf.empty:
        st.warning("No vessel data yet. Check that the Databricks gold views exist and the simulator has run.")
        return
    choice = st.selectbox("Vessel", ["All vessels"] + vdf.vessel_name.tolist())
    selected = None if choice == "All vessels" else choice

    st.subheader("Fleet overview")
    map_col, info_col = st.columns([3, 2])
    with map_col:
        st.pydeck_chart(build_map(vdf, selected), height=440)
        st.caption("  ".join(STATUS_LEGEND.values()) + "   Grey lines are planned routes.")
    with info_col:
        section_vessel_information(vdf, selected)

    left, right = st.columns([3, 2])
    with left:
        section_active_vessels(vdf)
    with right:
        st.subheader("Fleet status")
        section_counters(vdf)

    section_terminal_cargo()
    k = section_kpis()
    section_charts(k)
    section_insights(vdf)
    section_alerts()


def assistant_tab() -> None:
    st.subheader("BOGCL AI assistant")
    st.write("Ask about vessels, voyages, berths, tanks, cargo operations, delays, alerts and KPIs. "
             "Answers come from the operations data and show the SQL behind them.")
    ss = st.session_state
    ss.setdefault("chat", [])
    ss.setdefault("conversation_id", None)
    ss.setdefault("question_count", 0)

    if not ss.chat and "pending" not in ss:
        st.caption("Try one of these:")
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
        st.warning(f"This session reached the limit of {MAX_QUESTIONS_PER_SESSION} questions. Refresh the page to start again.")
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


def render_entry(entry: dict) -> None:
    with st.chat_message(entry["role"]):
        if entry.get("error"):
            st.error(entry["error"])
        for t in entry.get("text") or []:
            st.markdown(t)
        if entry.get("sql_description"):
            st.caption(entry["sql_description"])
        df = entry.get("df")
        if df is not None and not df.empty:
            st.dataframe(df, hide_index=True)
        elif entry.get("sql") and df is not None:
            st.info("The query returned no rows.")
        if entry.get("sql"):
            with st.expander("Show SQL"):
                st.code(entry["sql"], language="sql")


# --------------------------------------------------------------------------- page
check_secrets()
password_gate()

head = load(data.header)
title_col, time_col, btn_col = st.columns([4, 3, 1], vertical_alignment="center")
title_col.title("BOGCL Operations")
if head is not None and not head.empty:
    time_col.markdown(f"**{head.iloc[0].today}, {head.iloc[0].clock}** (GMT+6)  \nLatest data time")
if btn_col.button("Refresh data", width="stretch"):
    st.cache_data.clear()
    st.rerun()

tab_dash, tab_ai = st.tabs(["Operations dashboard", "AI assistant"])
with tab_dash:
    dashboard_tab()
with tab_ai:
    assistant_tab()

st.divider()
st.caption(st.secrets.get("FOOTER_NOTE", "Data source: simulated BOGCL operations feed on Databricks. Times are GMT+6."))
