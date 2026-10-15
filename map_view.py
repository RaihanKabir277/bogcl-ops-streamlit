"""Route map for the BOGCL dashboard (Leaflet inside a Streamlit iframe).

Markers are drawn in screen pixels (6 px for a vessel, 9 px for the selected one), so they stay small at every zoom level.
The base map follows the colour mode: CARTO dark tiles in dark mode, light tiles in light mode, and in Default mode it
follows the device setting and switches live.
"""
from __future__ import annotations

import html
import json

import pandas as pd

import theme

LEAFLET_CSS = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
LEAFLET_JS = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"


def _path(g: pd.DataFrame) -> list[list[float]]:
    return [[round(float(a), 4), round(float(b), 4)] for a, b in g.sort_values("seq")[["lat", "lon"]].values]


def build_map_html(vdf: pd.DataFrame, ports: pd.DataFrame | None, routes: pd.DataFrame | None,
                   selected: str | None, track: pd.DataFrame | None, mode: str, height: int = 360) -> str:
    fleet = []
    for r in vdf.itertuples():
        if pd.isna(r.lat) or pd.isna(r.lon):
            continue
        tip = f"<b>{html.escape(r.vessel_name)}</b><br>{html.escape(str(r.status))}, {0 if pd.isna(r.speed_kn) else r.speed_kn:.1f} kn"
        if r.status == "En Route" and isinstance(r.eta_local, str):
            tip += f"<br>to {html.escape(str(r.to_port))}, ETA {html.escape(r.eta_local)}"
        fleet.append({"name": r.vessel_name, "lat": float(r.lat), "lon": float(r.lon), "status": r.status, "tip": tip})

    port_list = []
    if ports is not None:
        port_list = [{"id": p.port_id, "name": p.port_name, "lat": float(p.lat), "lon": float(p.lon), "role": p.port_role}
                     for p in ports.itertuples()]

    all_routes, sel_route, sel_ports = [], [], []
    if routes is not None and not routes.empty:
        all_routes = [_path(g) for _, g in routes.groupby("route_id")]
    if selected:
        v = vdf[vdf.vessel_name == selected].iloc[0]
        if routes is not None and not routes.empty:
            same = routes[((routes.origin_port == v.origin_port) & (routes.dest_port == v.dest_port))
                          | ((routes.origin_port == v.dest_port) & (routes.dest_port == v.origin_port))]
            if not same.empty:
                sel_route = _path(same[same.route_id == same.route_id.iloc[0]])
        sel_ports = [v.origin_port, v.dest_port]

    data = {
        "mode": mode.lower(), "sel": selected, "fleet": fleet, "ports": port_list, "routes": all_routes,
        "selRoute": sel_route, "selPorts": sel_ports,
        "track": ([[round(float(a), 4), round(float(b), 4)] for a, b in track[["lat", "lon"]].values]
                  if track is not None and len(track) > 1 else []),
        "pal": theme.palettes_json(),
    }
    payload = json.dumps(data).replace("</", "<\\/")
    return (_TEMPLATE.replace("__CSS__", LEAFLET_CSS).replace("__JS__", LEAFLET_JS)
            .replace("__H__", str(height)).replace("__DATA__", payload))


_TEMPLATE = """<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="__CSS__">
<style>
html,body,#map{height:__H__px;margin:0;padding:0}
body{font-family:"Source Sans","Source Sans Pro",-apple-system,"Segoe UI",Roboto,Arial,sans-serif}
html[data-theme=dark]{--text:#EAF1FB;--muted:#9DB1CB;--panel:rgba(10,22,40,.92);--line:rgba(140,175,225,.30);--bgc:#06101D}
html[data-theme=light]{--text:#0E2238;--muted:#51647C;--panel:rgba(255,255,255,.95);--line:#C9D4E3;--bgc:#FFFFFF}
html[data-theme=dark] .leaflet-container{background:#0A1626}
html[data-theme=light] .leaflet-container{background:#DDE6F0}
.leaflet-container{font-family:inherit}
.leaflet-tooltip{background:var(--panel);color:var(--text);border:1px solid var(--line);border-radius:8px;box-shadow:0 4px 14px rgba(0,0,0,.25);font-size:12px;line-height:1.35;padding:6px 9px}
.leaflet-tooltip-top:before,.leaflet-tooltip-bottom:before,.leaflet-tooltip-left:before,.leaflet-tooltip-right:before{display:none}
.leaflet-tooltip.port-label{background:transparent;border:0;box-shadow:none;color:var(--text);font-weight:700;font-size:11.5px;padding:0;text-shadow:0 0 3px var(--bgc),0 0 3px var(--bgc),0 0 6px var(--bgc)}
.leaflet-tooltip.vessel-label{font-weight:700}
.leaflet-bar a,.leaflet-bar a:hover{background:var(--panel);color:var(--text);border-bottom:1px solid var(--line)}
.leaflet-control-attribution{background:var(--panel)!important;color:var(--muted)!important;font-size:10px}
.leaflet-control-attribution a{color:var(--muted)!important}
.legend{background:var(--panel);color:var(--text);border:1px solid var(--line);border-radius:10px;padding:8px 11px;font-size:12px;line-height:1.7}
.legend i{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:7px;border:1.5px solid #fff;vertical-align:-1px}
.legend s{display:inline-block;width:18px;height:0;border-top:2px dashed var(--muted);margin-right:7px;vertical-align:3px;text-decoration:none}
.legend u{display:inline-block;width:18px;height:3px;background:#4DABFF;margin-right:7px;vertical-align:2px;text-decoration:none}
</style></head>
<body><div id="map"></div>
<script src="__JS__"></script>
<script>
(function () {
  var D = __DATA__;
  var map = L.map('map', {zoomControl: true, minZoom: 2, worldCopyJump: false, zoomSnap: 0.25});
  map.attributionControl.setPrefix(false);
  var tile = null, overlay = L.layerGroup().addTo(map), legend = null;
  var mq = window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null;

  function dark() { return D.mode === 'dark' || (D.mode === 'default' && mq && mq.matches); }
  function pal() { return D.pal[dark() ? 'dark' : 'light']; }

  function draw() {
    var c = pal(), pts = [];
    var sc = {'En Route': c.good, 'At Anchor': c.warn, 'At Port': c.info};
    overlay.clearLayers();

    D.routes.forEach(function (r) {
      L.polyline(r, {color: c.muted, weight: 1.5, opacity: D.sel ? 0.25 : 0.55, dashArray: '5 6', interactive: false}).addTo(overlay);
      if (!D.sel) { r.forEach(function (p) { pts.push(p); }); }
    });
    if (D.selRoute.length) {
      L.polyline(D.selRoute, {color: c.good, weight: 3, opacity: 0.95, dashArray: '9 8', interactive: false}).addTo(overlay);
      D.selRoute.forEach(function (p) { pts.push(p); });
    }
    if (D.track.length) {
      L.polyline(D.track, {color: c.accent, weight: 3, opacity: 0.95, interactive: false}).addTo(overlay);
      D.track.forEach(function (p) { pts.push(p); });
    }

    D.ports.forEach(function (p) {
      var isSelPort = D.selPorts.indexOf(p.id) >= 0;
      if (D.sel && !isSelPort) { return; }
      var m = L.circleMarker([p.lat, p.lon], {radius: 4.5, color: c.text, weight: 1.5, fillColor: p.role === 'Origin' ? c.good : c.bad, fillOpacity: 1}).addTo(overlay);
      if (D.sel || p.role === 'Destination') {
        m.bindTooltip(p.name + (D.sel ? ' (' + (p.role === 'Origin' ? 'departure' : 'destination') + ')' : ''), {permanent: true, direction: 'bottom', offset: [0, 5], className: 'port-label'});
      } else {
        m.bindTooltip(p.name + ' (' + p.role.toLowerCase() + ')', {direction: 'top'});
      }
      if (D.sel) { pts.push([p.lat, p.lon]); }
    });

    D.fleet.forEach(function (v) {
      var col = sc[v.status] || c.muted, isSel = D.sel === v.name;
      if (D.sel && !isSel) {
        L.circleMarker([v.lat, v.lon], {radius: 4, color: '#ffffff', weight: 1, fillColor: col, fillOpacity: 0.35, opacity: 0.4, interactive: false}).addTo(overlay);
        return;
      }
      if (isSel) {
        L.circleMarker([v.lat, v.lon], {radius: 17, stroke: false, fillColor: col, fillOpacity: 0.25, interactive: false}).addTo(overlay);
      }
      var m = L.circleMarker([v.lat, v.lon], {radius: isSel ? 9 : 6, color: '#ffffff', weight: isSel ? 2.5 : 1.5, fillColor: col, fillOpacity: 1}).addTo(overlay);
      if (isSel) {
        m.bindTooltip(v.tip, {permanent: true, direction: 'top', offset: [0, -10], className: 'vessel-label'});
      } else {
        m.bindTooltip(v.tip, {direction: 'top', offset: [0, -6]});
      }
      pts.push([v.lat, v.lon]);
    });

    if (pts.length) { map.fitBounds(L.latLngBounds(pts), {padding: [34, 34], maxZoom: 7, animate: false}); }
    else { map.setView([15, 75], 3); }

    if (legend) { map.removeControl(legend); }
    legend = L.control({position: 'bottomleft'});
    legend.onAdd = function () {
      var d = L.DomUtil.create('div', 'legend');
      d.innerHTML = '<div><i style="background:' + c.good + '"></i>En route</div><div><i style="background:' + c.warn + '"></i>At anchor</div>' +
        '<div><i style="background:' + c.info + '"></i>At port</div><div><s></s>Planned route</div>' + (D.track.length ? '<div><u></u>Actual track</div>' : '');
      return d;
    };
    legend.addTo(map);
  }

  function apply() {
    document.documentElement.setAttribute('data-theme', dark() ? 'dark' : 'light');
    if (tile) { map.removeLayer(tile); }
    // Public OpenStreetMap tiles avoid a hosted-map API-key requirement.
    // Keep visible attribution, as required by the tile provider.
    tile = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
      {subdomains: 'abc', maxZoom: 19, attribution: '&copy; OpenStreetMap contributors'}).addTo(map);
    draw();
  }

  apply();
  if (mq && D.mode === 'default') {
    if (mq.addEventListener) { mq.addEventListener('change', apply); } else if (mq.addListener) { mq.addListener(apply); }
  }
})();
</script></body></html>
"""
