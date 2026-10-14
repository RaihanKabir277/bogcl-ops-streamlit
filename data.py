"""Data layer for the BOGCL Operations app.

Everything that talks to Databricks lives here:
  * one cached WorkspaceClient (host + personal access token from Streamlit secrets)
  * run_query(): runs SQL on your SQL warehouse and returns a pandas DataFrame
  * one small function per dashboard section

Times are stored in UTC in Delta. Every query converts to Asia/Dhaka (GMT+6) for display,
exactly like the Databricks dashboard datasets do.
"""
from __future__ import annotations

import time

import pandas as pd
import streamlit as st
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import (
    Disposition,
    ExecuteStatementRequestOnWaitTimeout,
    Format,
    StatementParameterListItem,
    StatementState,
)

NUMERIC_TYPES = {"BYTE", "SHORT", "INT", "LONG", "FLOAT", "DOUBLE", "DECIMAL"}
TIME_TYPES = {"DATE", "TIMESTAMP"}
QUERY_TIMEOUT_S = 120


# --------------------------------------------------------------------------- connection
def _host() -> str:
    host = st.secrets["DATABRICKS_HOST"].strip().rstrip("/")
    return host if host.startswith("http") else f"https://{host}"


@st.cache_resource(show_spinner=False)
def get_client() -> WorkspaceClient:
    """One client per app process. auth_type='pat' stops the SDK trying other login methods."""
    return WorkspaceClient(host=_host(), token=st.secrets["DATABRICKS_TOKEN"], auth_type="pat")


def fq() -> str:
    """Fully qualified schema, e.g. workspace.marine_ops"""
    return f"{st.secrets.get('CATALOG', 'workspace')}.{st.secrets.get('SCHEMA', 'marine_ops')}"


# --------------------------------------------------------------------------- results -> DataFrame
def statement_to_df(resp) -> pd.DataFrame:
    """Convert a Databricks StatementResponse (JSON_ARRAY, INLINE) to a typed DataFrame."""
    if resp.manifest is None or resp.manifest.schema is None or not resp.manifest.schema.columns:
        return pd.DataFrame()
    cols = resp.manifest.schema.columns
    rows = (resp.result.data_array if resp.result and resp.result.data_array else []) or []
    df = pd.DataFrame(rows, columns=[c.name for c in cols])
    for c in cols:
        tname = c.type_name.value if c.type_name is not None else "STRING"
        if tname in NUMERIC_TYPES:
            df[c.name] = pd.to_numeric(df[c.name], errors="coerce")
        elif tname == "BOOLEAN":
            df[c.name] = df[c.name].map({"true": True, "false": False, True: True, False: False})
        elif tname in TIME_TYPES:
            df[c.name] = pd.to_datetime(df[c.name], errors="coerce")
    return df


def _execute(sql: str, params: dict | None = None):
    w = get_client()
    plist = [StatementParameterListItem(name=k, value=str(v)) for k, v in (params or {}).items()] or None
    resp = w.statement_execution.execute_statement(
        statement=sql,
        warehouse_id=st.secrets["DATABRICKS_WAREHOUSE_ID"],
        wait_timeout="30s",
        on_wait_timeout=ExecuteStatementRequestOnWaitTimeout.CONTINUE,
        disposition=Disposition.INLINE,
        format=Format.JSON_ARRAY,
        parameters=plist,
    )
    deadline = time.time() + QUERY_TIMEOUT_S
    # A cold warehouse can take longer than 30 s to start: keep polling until it finishes.
    while resp.status.state in (StatementState.PENDING, StatementState.RUNNING):
        if time.time() > deadline:
            w.statement_execution.cancel_execution(resp.statement_id)
            raise TimeoutError("The SQL warehouse did not answer in time. Try again in a minute.")
        time.sleep(2)
        resp = w.statement_execution.get_statement(resp.statement_id)
    if resp.status.state != StatementState.SUCCEEDED:
        msg = resp.status.error.message if resp.status.error else str(resp.status.state)
        raise RuntimeError(f"Query failed: {msg}")
    return resp


@st.cache_data(ttl=60, show_spinner=False)
def run_query(sql: str, params: tuple = ()) -> pd.DataFrame:
    """Run SQL and cache the result for 60 s, so many visitors share one warehouse query."""
    return statement_to_df(_execute(sql, dict(params)))


def q(sql: str, **params) -> pd.DataFrame:
    return run_query(sql.format(fq=fq()), tuple(sorted(params.items())))


# --------------------------------------------------------------------------- dashboard queries
def header() -> pd.DataFrame:
    return q("""
        SELECT date_format(as_of_local, 'dd MMM yyyy')  AS today,
               date_format(as_of_local, 'hh:mm a')      AS clock
        FROM {fq}.gold_as_of""")


def vessels() -> pd.DataFrame:
    """One row per vessel with its current voyage (gold_vessel_latest) + display columns."""
    return q("""
        SELECT v.vessel_name, v.vessel_type, v.status, v.activity, v.lat, v.lon, v.speed_kn,
               v.voyage_id, v.voyage_type, v.product, v.cargo_mt,
               v.origin_port, v.dest_port, v.from_port, v.to_port,
               v.distance_nm, v.distance_covered_nm, v.pct_covered, v.avg_speed_kn,
               date_format(from_utc_timestamp(v.eta, 'Asia/Dhaka'), 'dd MMM, hh:mm a')         AS eta_local,
               date_format(from_utc_timestamp(v.planned_eta, 'Asia/Dhaka'), 'dd MMM, hh:mm a') AS planned_eta_local,
               round((unix_timestamp(v.eta) - unix_timestamp(a.as_of_utc)) / 3600, 1)         AS hours_to_arrival,
               round((unix_timestamp(v.eta) - unix_timestamp(v.planned_eta)) / 3600, 1)       AS eta_slip_hrs
        FROM {fq}.gold_vessel_latest v CROSS JOIN {fq}.gold_as_of a
        ORDER BY v.vessel_name""")


def ports() -> pd.DataFrame:
    return q("SELECT port_id, port_name, lat, lon, port_role FROM {fq}.dim_port")


def routes() -> pd.DataFrame:
    return q("SELECT route_id, origin_port, dest_port, seq, lat, lon FROM {fq}.route_path ORDER BY route_id, seq")


def track(voyage_id: str) -> pd.DataFrame:
    """Actual GPS breadcrumb of one voyage."""
    return q("""
        SELECT lat, lon FROM {fq}.vessel_positions
        WHERE voyage_id = :voyage_id ORDER BY event_ts LIMIT 5000""", voyage_id=voyage_id)


def berths() -> pd.DataFrame:
    return q("""
        SELECT b.berth_id, d.berth_name, d.berth_type, p.port_name, b.status, v.vessel_name,
               date_format(from_utc_timestamp(b.since_ts, 'Asia/Dhaka'), 'dd MMM, hh:mm a') AS occupied_since,
               o.product, round(100 * o.transferred_mt / o.planned_mt, 0) AS discharge_pct
        FROM {fq}.silver_berth_latest b
        JOIN {fq}.dim_berth d ON d.berth_id = b.berth_id
        JOIN {fq}.dim_port  p ON p.port_id  = b.port_id
        LEFT JOIN {fq}.dim_vessel v ON v.vessel_id = b.vessel_id
        LEFT JOIN {fq}.silver_op_latest o ON o.berth_id = b.berth_id AND o.status IN ('In Progress', 'Paused')
        ORDER BY b.berth_id""")


def bays() -> pd.DataFrame:
    return q("""
        SELECT count_if(status = 'Loading') AS busy, count_if(status = 'Maintenance') AS maintenance,
               count(*) AS total
        FROM {fq}.silver_bay_latest""")


def active_ops() -> pd.DataFrame:
    return q("""
        SELECT o.op_id, v.vessel_name, o.op_type, o.product, o.port_id, o.berth_id, o.tank_id,
               o.planned_mt, o.transferred_mt,
               round(100 * o.transferred_mt / o.planned_mt, 1) AS progress_pct,
               o.flow_rate_klph,
               date_format(from_utc_timestamp(o.start_ts, 'Asia/Dhaka'), 'dd MMM, hh:mm a')          AS started,
               date_format(from_utc_timestamp(o.est_completion_ts, 'Asia/Dhaka'), 'dd MMM, hh:mm a') AS est_completion,
               o.status
        FROM {fq}.silver_op_latest o JOIN {fq}.dim_vessel v ON v.vessel_id = o.vessel_id
        WHERE o.status IN ('In Progress', 'Paused')
        ORDER BY o.est_completion_ts""")


def cargo_today() -> pd.DataFrame:
    return q("""
        SELECT round(coalesce(sum(f.interval_mt), 0), 0) AS cargo_today_mt
        FROM {fq}.flow_readings f CROSS JOIN {fq}.gold_as_of a
        WHERE to_date(from_utc_timestamp(f.event_ts, 'Asia/Dhaka')) = a.as_of_date""")


def tanks() -> pd.DataFrame:
    return q("""
        SELECT tank_id, port_id, product, capacity_kl, volume_kl, level_pct, temperature_c
        FROM {fq}.silver_tank_latest ORDER BY tank_id""")


def kpis() -> pd.DataFrame:
    """Last 7 days + live today (gold_kpi_series)."""
    return q("""
        SELECT date_format(kpi_date, 'yyyy-MM-dd') AS kpi_date, fleet_utilization_pct, cargo_delivered_mt,
               on_time_pct, operational_delay_hrs, fuel_consumption_kl, critical_alerts, is_live
        FROM {fq}.gold_kpi_series
        WHERE kpi_date >= date_sub((SELECT as_of_date FROM {fq}.gold_as_of), 6)
        ORDER BY kpi_date""")


def alerts(limit: int = 60) -> pd.DataFrame:
    return q(f"""
        SELECT date_format(from_utc_timestamp(event_ts, 'Asia/Dhaka'), 'dd MMM, hh:mm a') AS time_dhaka,
               alert_id, severity, alert_type, asset_name, message
        FROM {{fq}}.alerts ORDER BY event_ts DESC LIMIT {int(limit)}""")


def alert_counts() -> pd.DataFrame:
    return q("""
        SELECT count_if(al.severity = 'Critical') AS critical_24h, count_if(al.severity = 'Warning') AS warning_24h
        FROM {fq}.alerts al CROSS JOIN {fq}.gold_as_of a
        WHERE al.event_ts >= a.as_of_utc - INTERVAL 24 HOURS""")
