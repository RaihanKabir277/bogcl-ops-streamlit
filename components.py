"""HTML building blocks for the BOGCL dashboard.

Every function returns an HTML string. Colours come from CSS variables defined in theme.py, so the same markup
looks right in Default, Dark and Light mode. Nothing here talks to Databricks.
"""
from __future__ import annotations

import html
import math

import pandas as pd

STATUS_TONE = {"En Route": "good", "At Anchor": "warn", "At Port": "info"}
BERTH_TONE = {"Occupied": "good", "Available": "warn"}
SEV_TONE = {"Critical": "bad", "Warning": "warn", "Info": "info"}
OP_TONE = {"In Progress": "info", "Paused": "warn", "Completed": "good"}

ICONS = {
    "calendar": '<rect x="3" y="4.5" width="18" height="16" rx="2"/><path d="M8 2.5v4M16 2.5v4M3 10h18"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "alert": '<path d="M12 3.5 22 20.5H2L12 3.5z"/><path d="M12 10v5"/><path d="M12 18v.01"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v5"/><path d="M12 8v.01"/>',
    "ship": '<path d="M3 17l1.6 3.2h14.8L21 17H3z"/><path d="M5.5 17v-5l6.5-3 6.5 3v5"/><path d="M12 9V4"/>',
    "route": '<circle cx="6" cy="18" r="2.4"/><circle cx="18" cy="6" r="2.4"/><path d="M8.4 18H14a3.5 3.5 0 0 0 0-7h-4a3.5 3.5 0 0 1 0-7h5.6"/>',
    "status": '<circle cx="12" cy="12" r="2.6"/><path d="M7.5 7.5a6.4 6.4 0 0 0 0 9M16.5 7.5a6.4 6.4 0 0 1 0 9"/>',
    "distance": '<path d="M4 20c0-6 8-4 8-10s6-5 8-6"/><circle cx="4" cy="20" r="1.6"/><circle cx="20" cy="4" r="1.6"/>',
    "hourglass": '<path d="M6 3h12M6 21h12M7 3c0 5 5 6 5 9s-5 4-5 9M17 3c0 5-5 6-5 9s5 4 5 9"/>',
    "speed": '<path d="M4 17a8 8 0 1 1 16 0"/><path d="M12 17l4-5"/>',
    "barrel": '<ellipse cx="12" cy="6" rx="7" ry="3"/><path d="M5 6v12c0 1.7 3.1 3 7 3s7-1.3 7-3V6"/><path d="M5 12c0 1.7 3.1 3 7 3s7-1.3 7-3"/>',
    "drop": '<path d="M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11z"/>',
    "pump": '<circle cx="12" cy="12" r="7"/><path d="M12 5v14M5 12h14"/>',
    "compass": '<circle cx="12" cy="12" r="9"/><path d="M15.5 8.5 13.6 13.6 8.5 15.5 10.4 10.4z"/>',
}


# --------------------------------------------------------------------------- helpers
def esc(v) -> str:
    return "" if v is None or (not isinstance(v, str) and pd.isna(v)) else html.escape(str(v))


def na(x) -> bool:
    return x is None or bool(pd.isna(x))


def n0(x) -> str:
    return "–" if na(x) else f"{float(x):,.0f}"


def n1(x) -> str:
    return "–" if na(x) else f"{float(x):,.1f}"


def duration(hours) -> str:
    if na(hours) or hours < 0:
        return "–"
    total = int(round(float(hours) * 60))
    d, rem = divmod(total, 1440)
    h, m = divmod(rem, 60)
    return (f"{d}d " if d else "") + f"{h}h {m:02d}m"


def ago(minutes) -> str:
    if na(minutes):
        return ""
    m = int(minutes)
    if m < 1:
        return "just now"
    if m < 60:
        return f"{m} min ago"
    if m < 1440:
        return f"{m // 60} h {m % 60:02d} min ago"
    return f"{m // 1440} d ago"


def ico(name: str, size: int = 18) -> str:
    return (f'<svg class="ic" viewBox="0 0 24 24" width="{size}" height="{size}" fill="none" stroke="currentColor" '
            f'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONS[name]}</svg>')


def pill(text, tone: str = "mute") -> str:
    return f'<span class="bc-pill bc-p-{tone}">{esc(text)}</span>'


def progress(pct, color: str = "var(--accent)") -> str:
    p = 0 if na(pct) else max(0.0, min(100.0, float(pct)))
    return (f'<div class="bc-prog"><div class="bc-bar"><i style="width:{p:.1f}%;background:{color}"></i></div>'
            f'<span>{p:.0f}%</span></div>')


def tile(label: str, value: str, sub: str = "", icon: str | None = None, small: bool = False, center: bool = False,
         value_html: bool = False) -> str:
    ic = ico(icon, 15) if icon else ""
    v = value if value_html else esc(value)
    return (f'<div class="bc-tile{" bc-c" if center else ""}"><div class="bc-k">{ic}{esc(label)}</div>'
            f'<div class="bc-v{" sm" if small else ""}">{v}</div>'
            + (f'<div class="bc-s">{esc(sub)}</div>' if sub else "") + "</div>")


def ring(pct, label: str = "", color: str = "var(--good)", size: int = 116, stroke: int = 11) -> str:
    p = 0.0 if na(pct) else max(0.0, min(100.0, float(pct)))
    r = (size - stroke) / 2
    c = 2 * math.pi * r
    mid = size / 2
    arc = (f'<circle cx="{mid}" cy="{mid}" r="{r:.2f}" fill="none" stroke-width="{stroke}" stroke-linecap="round" '
           f'stroke-dasharray="{c * p / 100:.2f} {c:.2f}" transform="rotate(-90 {mid} {mid})" style="stroke:{color}"/>') if p > 0 else ""
    return (f'<div class="bc-ring" style="width:{size}px;height:{size}px"><svg width="{size}" height="{size}" '
            f'viewBox="0 0 {size} {size}"><circle cx="{mid}" cy="{mid}" r="{r:.2f}" fill="none" stroke-width="{stroke}" '
            f'style="stroke:var(--track)"/>{arc}</svg><div class="bc-ring-c"><div class="bc-ring-v">{p:.0f}%</div>'
            f'{f"<div class=bc-ring-l>{esc(label)}</div>" if label else ""}</div></div>')


def ring_tile(title: str, pct, sub: str, color: str) -> str:
    return (f'<div class="bc-tile"><div class="bc-rt"><div class="bc-k">{esc(title)}</div>{ring(pct, color=color)}'
            f'<div class="bc-s">{esc(sub)}</div></div></div>')


def spark(values, color: str, w: int = 86, h: int = 34) -> str:
    v = [float(x) for x in values if not na(x)]
    if len(v) < 2:
        return ""
    lo, hi = min(v), max(v)
    rng = (hi - lo) or 1.0
    pts = [(2 + i * (w - 4) / (len(v) - 1), h - 4 - (x - lo) / rng * (h - 8)) for i, x in enumerate(v)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" aria-hidden="true"><polyline points="{line}" fill="none" '
            f'stroke-width="2" stroke-linejoin="round" stroke-linecap="round" style="stroke:{color}"/>'
            f'<circle cx="{pts[-1][0]:.1f}" cy="{pts[-1][1]:.1f}" r="3" style="fill:{color}"/></svg>')


def note(text: str, tone: str = "") -> str:
    return f'<div class="bc bc-note {tone}">{esc(text)}</div>'


def sql_details(sql: str) -> str:
    return f'<details class="bc bc-sql"><summary>Show SQL</summary><pre>{esc(sql)}</pre></details>'


def table(headers: list[tuple[str, str]], rows: list[str], max_h: int | None = None) -> str:
    """headers = [(label, css_class)], rows = list of '<tr>...</tr>' strings."""
    head = "".join(f'<th class="{c}">{esc(h)}</th>' for h, c in headers)
    style = f' style="max-height:{max_h}px"' if max_h else ""
    return f'<div class="bc-scroll"{style}><table class="bc-t"><thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'


def tr(cells: list[str], selected: bool = False) -> str:
    return f'<tr class="{"sel" if selected else ""}">' + "".join(cells) + "</tr>"


def td(content: str, cls: str = "", raw: bool = False) -> str:
    return f'<td class="{cls}">{content if raw else esc(content)}</td>'


# --------------------------------------------------------------------------- top bar
def head_html(today: str, clock: str, open_alerts: int) -> str:
    chip_cls = "bad" if open_alerts else "ok"
    return (f'<div class="bc bc-head"><div class="bc-brand"><div class="bc-logo">{ico("compass", 24)}</div><div>'
            f'<div class="bc-title">BOGCL Marine Operations</div><div class="bc-tag">Real-time vessel and terminal monitoring</div></div></div>'
            f'<span class="bc-chip">{ico("calendar")}{esc(today)}</span>'
            f'<span class="bc-chip">{ico("clock")}{esc(clock)} <span class="bc-dim">(GMT+6)</span></span>'
            f'<span class="bc-chip {chip_cls}" title="Critical and warning alerts in the last 24 hours">{ico("alert")}Alerts ({int(open_alerts)})</span></div>')


# --------------------------------------------------------------------------- fleet
def voyage_strip(vdf: pd.DataFrame, selected: str | None) -> str:
    """The row of tiles under the map: one vessel's voyage, or a fleet summary when 'All Vessels' is selected."""
    if selected:
        r = vdf[vdf.vessel_name == selected].iloc[0]
        if r.status == "En Route":
            tta, tta_sub = duration(r.hours_to_arrival), "to arrival"
        elif r.status in ("At Anchor", "At Port"):
            tta, tta_sub = "Arrived", f"{r.status.lower()}"
        else:
            tta, tta_sub = "–", "not yet departed"
        dist = "–" if na(r.distance_nm) else f"{n0(r.distance_covered_nm)} NM"
        dist_sub = "" if na(r.distance_nm) else f"of {n0(r.distance_nm)} NM ({n0(r.pct_covered)}%)"
        slip = "" if na(r.eta_slip_hrs) else f"{r.eta_slip_hrs:+.1f} h vs plan"
        eta = r.eta_local if isinstance(r.eta_local, str) else "–"
        return ('<div class="bc bc-tiles bc-t7">'
                + tile("Vessel", r.vessel_name, f"IMO {r.imo}" if not na(r.imo) else "", "ship", small=True)
                + tile("Voyage", r.voyage_id if isinstance(r.voyage_id, str) else "–", f"{r.voyage_type} voyage", "route", small=True)
                + tile("Voyage status", r.status, str(r.activity), "status", small=True)
                + tile("Distance covered", dist, dist_sub, "distance", small=True)
                + tile(f"ETA ({r.to_port})", eta, slip, "clock", small=True)
                + tile("Time to arrival", tta, tta_sub, "hourglass", small=True)
                + tile("Avg speed", f"{n1(r.avg_speed_kn)} kn", "voyage average", "speed", small=True) + "</div>")
    er = vdf[vdf.status == "En Route"]
    laden = vdf[vdf.voyage_type == "Laden"]
    anchored = vdf[vdf.status == "At Anchor"]
    covered, total = er.distance_covered_nm.sum(), er.distance_nm.sum()
    nxt = er[er.hours_to_arrival > 0].sort_values("hours_to_arrival").head(1)
    nxt_v = nxt.iloc[0].vessel_name if not nxt.empty else "–"
    nxt_s = f"in {duration(nxt.iloc[0].hours_to_arrival)} at {nxt.iloc[0].to_port}" if not nxt.empty else ""
    wait = anchored.anchor_wait_hrs.max() if not anchored.empty else None
    return ('<div class="bc bc-tiles bc-t7">'
            + tile("Fleet", f"{len(vdf)} vessels", f"{len(laden)} laden, {len(vdf) - len(laden)} ballast", "ship", small=True)
            + tile("Voyages under way", f"{len(er)}", f"{(100 * covered / total) if total else 0:.0f}% of distance covered", "route", small=True)
            + tile("At anchor", f"{len(anchored)}", f"longest wait {n1(wait)} h" if not na(wait) else "none waiting", "status", small=True)
            + tile("Next arrival", nxt_v, nxt_s, "clock", small=True)
            + tile("Avg speed", f"{n1(er.speed_kn.mean())} kn", "vessels under way", "speed", small=True)
            + tile("Cargo on laden voyages", f"{n0(laden.cargo_mt.sum())} MT", "all laden vessels", "barrel", small=True)
            + tile("Arriving today", f"{int(vdf.eta_today.sum())}", "ETA within today (GMT+6)", "hourglass", small=True) + "</div>")


def fleet_ops_card(vdf: pd.DataFrame, selected: str | None, list_height: int = 300) -> str:
    counts = vdf.status.value_counts()
    tiles = ('<div class="bc-tiles bc-t4">'
             + tile("Live positions", f"{len(vdf)}", "vessels", center=True)
             + tile("Current voyages", f"{int(counts.get('En Route', 0))}", "en route", center=True)
             + tile("At anchor", f"{int(counts.get('At Anchor', 0))}", "vessels", center=True)
             + tile("ETA today", f"{int(vdf.eta_today.sum())}", "vessels", center=True) + "</div>")
    order = {"En Route": 0, "At Anchor": 1, "At Port": 2}
    d = vdf.assign(_o=vdf.status.map(order).fillna(9)).sort_values(["_o", "hours_to_arrival"])
    rows = [tr([td(r.vessel_name), td(pill(r.status, STATUS_TONE.get(r.status, "mute")), raw=True), td(r.from_port),
                td(r.to_port), td(r.eta_local if isinstance(r.eta_local, str) else "–"),
                td(f"{n1(r.speed_kn)} kn", "n")], selected=(r.vessel_name == selected)) for r in d.itertuples()]
    tbl = table([("Vessel", ""), ("Status", ""), ("From", ""), ("To", ""), ("ETA (GMT+6)", ""), ("Speed", "n")], rows, list_height)
    return (f'<div class="bc bc-card" style="min-height:560px"><div class="bc-ph"><span>Fleet operations</span></div>{tiles}'
            f'<div class="bc-ph" style="margin:16px 0 8px"><span>Active vessel list</span></div>{tbl}</div>')


def fleet_table_card(vdf: pd.DataFrame, selected: str | None) -> str:
    order = {"En Route": 0, "At Anchor": 1, "At Port": 2}
    d = vdf.assign(_o=vdf.status.map(order).fillna(9)).sort_values(["_o", "hours_to_arrival"])
    rows = []
    for r in d.itertuples():
        slip = "–" if na(r.eta_slip_hrs) else f"{r.eta_slip_hrs:+.1f} h"
        rows.append(tr([td(r.vessel_name), td(r.vessel_type), td(pill(r.status, STATUS_TONE.get(r.status, "mute")), raw=True),
                        td(r.activity), td(r.voyage_id if isinstance(r.voyage_id, str) else "–"),
                        td(r.product if isinstance(r.product, str) else "Ballast"), td(n0(r.cargo_mt), "n"),
                        td(r.from_port), td(r.to_port), td(progress(r.pct_covered), raw=True),
                        td(f"{n1(r.speed_kn)} kn", "n"), td(r.eta_local if isinstance(r.eta_local, str) else "–"),
                        td(slip, "n")], selected=(r.vessel_name == selected)))
    hdr = [("Vessel", ""), ("Type", ""), ("Status", ""), ("Activity", ""), ("Voyage", ""), ("Cargo", ""), ("MT", "n"), ("From", ""),
           ("To", ""), ("Voyage progress", ""), ("Speed", "n"), ("ETA (GMT+6)", ""), ("ETA vs plan", "n")]
    return f'<div class="bc bc-card"><div class="bc-ph"><span>All vessels</span></div>{table(hdr, rows, 520)}</div>'


def queue_card(vdf: pd.DataFrame) -> str:
    a = vdf[vdf.status == "At Anchor"].sort_values("anchor_wait_hrs", ascending=False)
    if a.empty:
        body = '<div class="bc-note">No vessel is waiting at anchorage.</div>'
    else:
        rows = []
        for r in a.itertuples():
            w = r.anchor_wait_hrs
            tone, txt = ("good", "Within free time") if w <= 6 else (("warn", "Waiting") if w <= 24 else ("bad", "Long wait"))
            rows.append(tr([td(r.vessel_name), td(r.to_port), td(r.product), td(n0(r.cargo_mt), "n"), td(f"{n1(w)} h", "n"),
                            td(pill(txt, tone), raw=True)]))
        body = table([("Vessel", ""), ("Port", ""), ("Cargo", ""), ("MT", "n"), ("Waiting", "n"), ("Berth wait", "")], rows)
    return (f'<div class="bc bc-card"><div class="bc-ph"><span>Anchorage queue</span>'
            f'<span class="bc-sub">6 h free time, alert after 24 h</span></div>{body}</div>')


# --------------------------------------------------------------------------- terminal
def berth_table(berths: pd.DataFrame, max_h: int | None = None) -> str:
    rows = [tr([td(r.berth_name), td(r.port_name), td(pill(r.status, BERTH_TONE.get(r.status, "mute")), raw=True),
                td(r.vessel_name if isinstance(r.vessel_name, str) else "–"),
                td(r.occupied_since if isinstance(r.occupied_since, str) else "–"),
                td("–" if na(r.hours_at_berth) or r.status != "Occupied" else f"{n1(r.hours_at_berth)} h", "n")])
            for r in berths.itertuples()]
    return table([("Berth", ""), ("Port", ""), ("Status", ""), ("Current vessel", ""), ("Start (GMT+6)", ""), ("At berth", "n")], rows, max_h)


def terminal_card(berths: pd.DataFrame | None, bays: pd.DataFrame | None, ta: pd.DataFrame | None) -> str:
    tiles = []
    if berths is not None and not berths.empty:
        occ = int((berths.status == "Occupied").sum())
        tiles.append(ring_tile("Berth occupancy", 100 * occ / len(berths), f"{occ} / {len(berths)} berths", "var(--good)"))
    if bays is not None and not bays.empty:
        b = bays.iloc[0]
        tiles.append(ring_tile("Loading bay utilisation", 100 * b.busy / b.total, f"{int(b.busy)} / {int(b.total)} bays loading", "var(--accent)"))
    if ta is not None and not ta.empty:
        t = ta.iloc[0]
        val = "–" if na(t.turnaround_hrs) else f"{t.turnaround_hrs:.1f}<small>hrs</small>"
        tiles.append(f'<div class="bc-tile"><div class="bc-rt"><div class="bc-k">Turnaround time</div>'
                     f'<div class="bc-v" style="margin:34px 0 0">{val}</div>'
                     f'<div class="bc-s" style="margin-top:34px">{int(t.vessels_handled_7d)} discharges completed, last 7 days</div></div></div>')
    tbl = berth_table(berths) if berths is not None and not berths.empty else ""
    return (f'<div class="bc bc-card"><div class="bc-ph"><span>Terminal operations</span></div>'
            f'<div class="bc-tiles bc-t3">{"".join(tiles)}</div>'
            f'<div class="bc-ph" style="margin:16px 0 8px"><span>Berth and status</span></div>{tbl}</div>')


# --------------------------------------------------------------------------- cargo
def band(level: float) -> tuple[str, str]:
    if level >= 95:
        return "var(--bad)", "Critical"
    if level >= 90:
        return "var(--warn)", "High"
    if level <= 15:
        return "var(--info)", "Low"
    return "var(--good)", "Normal"


def tank_bars(t: pd.DataFrame) -> str:
    cols, labs = [], []
    for r in t.itertuples():
        pct = 0 if na(r.level_pct) else max(0.0, min(100.0, float(r.level_pct)))
        color, name = band(pct)
        tip = f"{r.tank_id} ({r.product}, {r.port_id}): {pct:.1f}% - {name}"
        cols.append(f'<div class="bc-bcol" title="{esc(tip)}"><div class="bc-bfill" style="height:{pct:.1f}%;background:{color}"></div>'
                    f'<div class="bc-bval" style="bottom:calc({pct:.1f}% + 3px)">{pct:.0f}%</div></div>')
        labs.append(f"<div>{esc(str(r.tank_id).replace('TK-', 'TK'))}</div>")
    ticks = "".join(f'<div class="bc-ya" style="top:{100 - v}%">{v}%</div>' for v in (100, 75, 50, 25, 0))
    legend = ('<div class="bc-legend"><span><i style="background:var(--good)"></i>Normal</span>'
              '<span><i style="background:var(--warn)"></i>High 90%+</span><span><i style="background:var(--bad)"></i>Critical 95%+</span>'
              '<span><i style="background:var(--info)"></i>Low 15% or less</span></div>')
    return (f'{legend}<div class="bc-plot">{ticks}<div class="bc-bars">{"".join(cols)}</div></div>'
            f'<div class="bc-blabs">{"".join(labs)}</div>')


def ops_table(ops: pd.DataFrame, selected: str | None = None, max_h: int | None = 260) -> str:
    if ops is None or ops.empty:
        return '<div class="bc-note">No cargo operation is running right now.</div>'
    rows = [tr([td(r.vessel_name), td(pill(r.op_type, "info" if r.op_type == "Discharge" else "warn"), raw=True), td(r.product),
                td(n0(r.planned_mt), "n"), td(progress(r.progress_pct), raw=True), td(r.started), td(r.est_completion)],
               selected=(r.vessel_name == selected)) for r in ops.itertuples()]
    return table([("Vessel", ""), ("Operation", ""), ("Product", ""), ("Planned MT", "n"), ("Progress", ""),
                  ("Start (GMT+6)", ""), ("Est. completion", "")], rows, max_h)


def cargo_card(ops: pd.DataFrame | None, tanks: pd.DataFrame | None, today_mt, status: str, selected: str | None) -> str:
    prog_pct, prog_label, prog_sub = 0.0, "All discharges", "no active discharge"
    if ops is not None and not ops.empty:
        mine = ops[ops.vessel_name == selected] if selected else ops.iloc[0:0]
        if selected and not mine.empty:
            o = mine.iloc[0]
            prog_pct, prog_label = float(o.progress_pct), selected
            prog_sub = f"{n0(o.transferred_mt)} / {n0(o.planned_mt)} MT"
        elif selected:
            prog_label, prog_sub = selected, "no active cargo operation"
        else:
            dis = ops[ops.op_type == "Discharge"]
            if not dis.empty and dis.planned_mt.sum() > 0:
                prog_pct = 100 * dis.transferred_mt.sum() / dis.planned_mt.sum()
                prog_label = "All discharges"
                prog_sub = f"{n0(dis.transferred_mt.sum())} / {n0(dis.planned_mt.sum())} MT"
    avg_lvl = None
    if tanks is not None and not tanks.empty and tanks.capacity_kl.sum() > 0:
        avg_lvl = 100 * tanks.volume_kl.sum() / tanks.capacity_kl.sum()
    sys_tone = "good" if status == "Normal" else "warn"
    t1 = (f'<div class="bc-tile"><div class="bc-rt"><div class="bc-k">Loading / offloading progress</div>'
          f'{ring(prog_pct, color="var(--good)")}<div class="bc-s"><b>{esc(prog_label)}</b><br>{esc(prog_sub)}</div></div></div>')
    t2 = (f'<div class="bc-tile bc-c"><div class="bc-k">Cargo quantity transferred</div><div style="margin:14px 0 4px;color:var(--accent)">{ico("barrel", 40)}</div>'
          f'<div class="bc-v">{n0(today_mt)}<small>MT</small></div><div class="bc-s">today (GMT+6)</div></div>')
    t3 = ring_tile("Tank level (avg)", avg_lvl, "of total tank capacity", "var(--accent-2)")
    t4 = (f'<div class="bc-tile bc-c"><div class="bc-k">Systems</div><div style="margin:14px 0 8px;color:var(--{sys_tone})">{ico("pump", 40)}</div>'
          f'<div class="bc-v sm">{pill("All systems normal" if status == "Normal" else "Attention needed", sys_tone)}</div>'
          f'<div class="bc-s" style="margin-top:8px">no critical alert in the last 2 h</div></div>')
    bars = tank_bars(tanks) if tanks is not None and not tanks.empty else ""
    return (f'<div class="bc bc-card"><div class="bc-ph"><span>Cargo operations</span></div>'
            f'<div class="bc-tiles bc-t4">{t1}{t2}{t3}{t4}</div>'
            f'<div class="bc-grid" style="grid-template-columns:minmax(0,5fr) minmax(0,6fr);margin-top:14px">'
            f'<div><div class="bc-ph" style="margin:0 0 8px"><span>Tank levels overview</span></div>{bars}</div>'
            f'<div><div class="bc-ph" style="margin:0 0 8px"><span>Active cargo operations</span></div>{ops_table(ops, selected)}</div></div></div>')


def tank_table_card(t: pd.DataFrame) -> str:
    rows = []
    for r in t.itertuples():
        color, name = band(0 if na(r.level_pct) else float(r.level_pct))
        rows.append(tr([td(r.tank_id), td(r.port_id), td(r.product), td(n0(r.capacity_kl), "n"), td(n0(r.volume_kl), "n"),
                        td(progress(r.level_pct, color), raw=True), td(n1(r.temperature_c), "n")]))
    return (f'<div class="bc bc-card"><div class="bc-ph"><span>Tank detail</span></div>'
            f'{table([("Tank", ""), ("Port", ""), ("Product", ""), ("Capacity (KL)", "n"), ("Volume (KL)", "n"), ("Level", ""), ("Temp (C)", "n")], rows)}</div>')


# --------------------------------------------------------------------------- KPIs, trend, alerts
def exec_kpi_card(k: pd.DataFrame | None, clock: str = "") -> str:
    if k is None or k.empty:
        return '<div class="bc bc-card"><div class="bc-ph"><span>Executive KPIs</span></div><div class="bc-note">No KPI data yet.</div></div>'
    live = k[k.is_live == True]  # noqa: E712
    today = (live if not live.empty else k).iloc[-1]
    prev = k[k.kpi_date < today.kpi_date]
    y = prev.iloc[-1] if not prev.empty else None

    def ratio(label, col, color):
        d = "" if y is None else today[col] - y[col]
        if d == "":
            dh = ""
        else:
            cls = "bc-up" if d > 0.05 else ("bc-down" if d < -0.05 else "bc-flat")
            arrow = "▲" if d > 0.05 else ("▼" if d < -0.05 else "■")
            dh = f'<div class="bc-delta {cls}">{arrow} {abs(d):.1f} pts <span>vs yesterday</span></div>'
        return (f'<div class="bc-tile"><div class="bc-k">{label}</div><div class="bc-kpi"><div>'
                f'<div class="bc-v">{today[col]:.0f}<small>%</small></div>{dh}</div>{spark(k[col], color)}</div></div>')

    def total(label, col, unit, fmt, color):
        yv = "" if y is None else f'<div class="bc-delta bc-flat"><span>Yesterday {fmt(y[col])}</span></div>'
        return (f'<div class="bc-tile"><div class="bc-k">{label}</div><div class="bc-kpi"><div>'
                f'<div class="bc-v">{fmt(today[col])}<small>{unit}</small></div>{yv}</div>{spark(k[col], color)}</div></div>')

    tiles = (ratio("Fleet utilisation", "fleet_utilization_pct", "var(--good)")
             + total("Cargo delivered", "cargo_delivered_mt", "MT", n0, "var(--accent)")
             + ratio("On-time delivery", "on_time_pct", "var(--accent)")
             + total("Operational delays", "operational_delay_hrs", "hrs", n1, "var(--warn)")
             + total("Fuel consumption", "fuel_consumption_kl", "KL", n1, "var(--accent-2)")
             + total("Critical alerts", "critical_alerts", "", n0, "var(--bad)"))
    foot = (f'Today is a partial day{f" (as of {esc(clock)})" if clock else ""}. Cargo, delay, fuel and alert totals build up through the day, '
            f'so they sit beside yesterday\'s full-day figure instead of showing a percentage change.')
    return (f'<div class="bc bc-card"><div class="bc-ph"><span>Executive KPIs</span><span class="bc-sub">today</span></div>'
            f'<div class="bc-tiles bc-t2">{tiles}</div><div class="bc-foot">{foot}</div></div>')


def _nice(x: float) -> float:
    for s in (5, 10, 15, 20, 25, 30, 40, 50, 60, 80, 100, 150, 200):
        if x <= s:
            return float(s)
    return float(math.ceil(x / 100) * 100)


def trend_card(k: pd.DataFrame | None) -> str:
    if k is None or len(k) < 2:
        return '<div class="bc bc-card"><div class="bc-ph"><span>KPI trend</span></div><div class="bc-note">Not enough history yet.</div></div>'
    W, H, L, R, T, B = 640, 270, 44, 46, 14, 34
    n = len(k)
    xs = [L + i * (W - L - R) / (n - 1) for i in range(n)]
    ymax_r = _nice(max(float(k.operational_delay_hrs.max()), 1.0) * 1.15)

    def yl(v):  # left axis 0..100 %
        return T + (H - T - B) * (1 - float(v) / 100)

    def yr(v):  # right axis 0..ymax_r hours
        return T + (H - T - B) * (1 - float(v) / ymax_r)

    grid, ticks = [], []
    for i in range(5):
        gy = T + (H - T - B) * i / 4
        grid.append(f'<line x1="{L}" x2="{W - R}" y1="{gy:.1f}" y2="{gy:.1f}" style="stroke:var(--line)" stroke-width="1"/>')
        ticks.append(f'<text x="{L - 8}" y="{gy + 4:.1f}" text-anchor="end">{100 - i * 25}</text>')
        ticks.append(f'<text x="{W - R + 8}" y="{gy + 4:.1f}" text-anchor="start">{ymax_r * (4 - i) / 4:g}</text>')
    xl = "".join(f'<text x="{xs[i]:.1f}" y="{H - 10}" text-anchor="middle">{esc(k.kpi_label.iloc[i])}</text>' for i in range(n))

    def series(col, ycalc, color, name, unit):
        pts = [(xs[i], ycalc(k[col].iloc[i])) for i in range(n)]
        solid = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts[:-1])
        out = [f'<polyline points="{solid}" fill="none" stroke-width="2.4" stroke-linejoin="round" style="stroke:{color}"/>']
        out.append(f'<line x1="{pts[-2][0]:.1f}" y1="{pts[-2][1]:.1f}" x2="{pts[-1][0]:.1f}" y2="{pts[-1][1]:.1f}" stroke-width="2.4" '
                   f'stroke-dasharray="5 5" style="stroke:{color}"/>')
        for i, (x, y) in enumerate(pts):
            last = i == n - 1
            tip = f"{k.kpi_label.iloc[i]}: {name} {float(k[col].iloc[i]):.1f} {unit}" + (" (today, partial day)" if last else "")
            fill = "var(--card-solid)" if last else color
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{4.2 if last else 3}" stroke-width="2" style="stroke:{color};fill:{fill}">'
                       f'<title>{esc(tip)}</title></circle>')
        return "".join(out)

    svg = (f'<svg class="bc-chart" viewBox="0 0 {W} {H}" role="img" aria-label="Seven day KPI trend">{"".join(grid)}{"".join(ticks)}{xl}'
           f'{series("operational_delay_hrs", yr, "var(--warn)", "Operational delays", "hrs")}'
           f'{series("on_time_pct", yl, "var(--accent)", "On-time delivery", "%")}'
           f'{series("fleet_utilization_pct", yl, "var(--good)", "Fleet utilisation", "%")}</svg>')
    legend = ('<div class="bc-legend"><span><i style="background:var(--good)"></i>Fleet utilisation (%)</span>'
              '<span><i style="background:var(--accent)"></i>On-time delivery (%)</span>'
              '<span><i style="background:var(--warn)"></i>Operational delays (hrs, right axis)</span></div>')
    return (f'<div class="bc bc-card"><div class="bc-ph"><span>KPI trend</span><span class="bc-sub">last 7 days</span></div>{legend}{svg}'
            f'<div class="bc-foot">Hollow dashed point = today, partial day.</div></div>')


def alert_icon(sev: str) -> str:
    tone = SEV_TONE.get(sev, "info")
    name = "alert" if sev in ("Critical", "Warning") else "info"
    return f'<div class="bc-al-ic" style="background:var(--{tone}-bg);color:var(--{tone})">{ico(name, 17)}</div>'


def alerts_card(al: pd.DataFrame | None, limit: int = 7, height: int = 420) -> str:
    if al is None or al.empty:
        body = '<div class="bc-note">No alerts yet.</div>'
    else:
        items = [f'<div class="bc-al">{alert_icon(r.severity)}<div class="bc-al-b"><div class="bc-al-t" title="{esc(r.message)}">{esc(r.alert_type)}</div>'
                 f'<div class="bc-al-s">{esc(r.asset_name)}</div></div><div class="bc-al-w">{esc(ago(r.minutes_ago))}</div></div>'
                 for r in al.head(limit).itertuples()]
        body = f'<div class="bc-scroll" style="max-height:{height}px">{"".join(items)}</div>'
    return f'<div class="bc bc-card"><div class="bc-ph"><span>Latest alerts</span></div>{body}</div>'


def alerts_table_card(al: pd.DataFrame | None) -> str:
    if al is None or al.empty:
        return '<div class="bc bc-card"><div class="bc-note">No alerts yet.</div></div>'
    rows = [tr([td(r.time_dhaka), td(pill(r.severity, SEV_TONE.get(r.severity, "mute")), raw=True), td(r.alert_type),
                td(r.asset_name), td(r.message)]) for r in al.itertuples()]
    return (f'<div class="bc bc-card"><div class="bc-ph"><span>Alert log</span><span class="bc-sub">newest first</span></div>'
            f'{table([("Time (GMT+6)", ""), ("Severity", ""), ("Type", ""), ("Asset", ""), ("Message", "")], rows, 640)}</div>')


def count_tiles(items: list[tuple[str, str, str]]) -> str:
    """items = [(label, value, sub)]"""
    return f'<div class="bc bc-tiles bc-t{min(len(items), 4)}">' + "".join(tile(a, b, c, center=True) for a, b, c in items) + "</div>"


def fmt_cell(v) -> str:
    if na(v):
        return ""
    if isinstance(v, bool):
        return "Yes" if v else "No"
    if isinstance(v, (int,)) or (isinstance(v, float) and float(v).is_integer() and abs(v) >= 1000):
        return f"{int(v):,}"
    if isinstance(v, float):
        return f"{v:,.2f}".rstrip("0").rstrip(".")
    return str(v)


def df_table(df: pd.DataFrame, max_h: int = 420) -> str:
    """Render any DataFrame (for example a Genie result) with the dashboard's own table style."""
    headers = [(str(c), "n" if pd.api.types.is_numeric_dtype(df[c]) and not pd.api.types.is_bool_dtype(df[c]) else "") for c in df.columns]
    rows = [tr([td(fmt_cell(v), h[1]) for v, h in zip(rec, headers)]) for rec in df.itertuples(index=False, name=None)]
    return f'<div class="bc">{table(headers, rows, max_h)}</div>'
