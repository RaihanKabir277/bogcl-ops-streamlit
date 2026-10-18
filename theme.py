"""Colour modes for the BOGCL dashboard.

Three modes, chosen by the viewer in the top bar:
  Default - follows the device / browser setting (light or dark) automatically
  Dark    - always dark
  Light   - always light

Everything is driven by CSS variables, so the cards, tables, charts, map controls and Streamlit's own widgets
all switch together. Text colours are chosen for contrast: roughly 4.5:1 or better on their backgrounds in both modes.
"""
from __future__ import annotations

MODES = ["Default", "Dark", "Light"]

DARK = {
    "bg-solid": "#06101D",
    "page-bg": ("radial-gradient(1100px 620px at 6% -8%, rgba(36,99,190,.34) 0%, rgba(36,99,190,0) 62%),"
                "radial-gradient(900px 560px at 104% 2%, rgba(18,162,170,.22) 0%, rgba(18,162,170,0) 58%),"
                "linear-gradient(180deg,#07121F 0%,#050C16 100%)"),
    "card": "rgba(14,27,47,.86)", "card-solid": "#0E1B2F", "tile": "rgba(255,255,255,.045)", "field": "#112440",
    "border": "rgba(140,175,225,.22)", "line": "rgba(140,175,225,.13)", "track": "rgba(140,175,225,.18)",
    "text": "#EAF1FB", "muted": "#9DB1CB", "accent": "#4DABFF", "accent-2": "#2BD4C7",
    "good": "#3DDC97", "warn": "#FFB547", "bad": "#FF6B6B", "info": "#5CB6FF",
    "good-bg": "rgba(61,220,151,.15)", "warn-bg": "rgba(255,181,71,.16)", "bad-bg": "rgba(255,107,107,.17)",
    "info-bg": "rgba(92,182,255,.17)", "rail": "#081629", "hover": "rgba(120,170,235,.16)",
    "shadow": "0 10px 30px rgba(0,0,0,.38)", "on-accent": "#04121F", "scheme": "dark",
}

LIGHT = {
    "bg-solid": "#EEF3F9",
    "page-bg": ("radial-gradient(1000px 560px at 6% -10%, rgba(52,120,220,.17) 0%, rgba(52,120,220,0) 62%),"
                "radial-gradient(900px 520px at 104% 0%, rgba(20,170,170,.13) 0%, rgba(20,170,170,0) 58%),"
                "linear-gradient(180deg,#F5F8FC 0%,#E8EEF6 100%)"),
    "card": "rgba(255,255,255,.94)", "card-solid": "#FFFFFF", "tile": "#F2F6FB", "field": "#FFFFFF",
    "border": "#D3DDEA", "line": "#E3E9F2", "track": "#DFE7F1",
    "text": "#0E2238", "muted": "#51647C", "accent": "#0A64C8", "accent-2": "#0A8F8A",
    "good": "#11804D", "warn": "#A86200", "bad": "#C42B2B", "info": "#0A64C8",
    "good-bg": "rgba(17,128,77,.11)", "warn-bg": "rgba(168,98,0,.12)", "bad-bg": "rgba(196,43,43,.10)",
    "info-bg": "rgba(10,100,200,.10)", "rail": "#FFFFFF", "hover": "rgba(10,100,200,.08)",
    "shadow": "0 6px 22px rgba(20,50,90,.09)", "on-accent": "#FFFFFF", "scheme": "light",
}


def _vars(p: dict) -> str:
    body = ";".join(f"--{k}:{v}" for k, v in p.items() if k != "scheme")
    return f"{body};color-scheme:{p['scheme']}"


def build_css(mode: str) -> str:
    """Return the full <style> body for the chosen mode."""
    if mode == "Dark":
        root = f":root{{{_vars(DARK)}}}"
    elif mode == "Light":
        root = f":root{{{_vars(LIGHT)}}}"
    else:  # Default: light, switching to dark when the device prefers dark
        root = f":root{{{_vars(LIGHT)}}}@media (prefers-color-scheme: dark){{:root{{{_vars(DARK)}}}}}"
    return root + BASE_CSS


def palettes_json() -> dict:
    """Palettes handed to the map iframe (it cannot see the page's CSS variables)."""
    keep = ["good", "warn", "bad", "info", "accent", "text", "muted", "card-solid", "border"]
    return {"dark": {k: DARK[k] for k in keep}, "light": {k: LIGHT[k] for k in keep}}


BASE_CSS = """
/* ===== Streamlit chrome ===== */
.stApp{background:var(--page-bg)!important;background-attachment:fixed!important;color:var(--text)}
[data-testid="stAppViewContainer"],[data-testid="stMain"]{background:transparent!important}
[data-testid="stHeader"]{background:transparent!important}
[data-testid="stToolbar"],[data-testid="stDecoration"]{display:none!important}
[data-testid="stMainBlockContainer"]{padding:1.0rem 1.4rem 3rem!important;max-width:1780px}
[data-testid="stElementContainer"]:has(.css-host){display:none!important}
.stApp,.stApp p,.stApp li,.stApp label,.stMarkdown,[data-testid="stWidgetLabel"] *{color:var(--text)}
.stApp h1,.stApp h2,.stApp h3,.stApp h4{color:var(--text)}
.stMarkdown table{border-collapse:collapse}
.stMarkdown th,.stMarkdown td{border:1px solid var(--border)!important;padding:6px 10px;color:var(--text)!important;background:transparent!important}
.stMarkdown a{color:var(--accent)}
[data-testid="stSpinner"] *{color:var(--text)!important}

/* sidebar = left navigation rail */
[data-testid="stSidebar"],[data-testid="stSidebar"]>div{background:var(--rail)!important}
[data-testid="stSidebar"]{border-right:1px solid var(--border)}
[data-testid="stSidebar"] *{color:var(--text)}
[data-testid="stSidebarNavLink"]{background:transparent!important;border-radius:10px;margin:2px 6px}
[data-testid="stSidebarNavLink"]:hover{background:var(--hover)!important}
[data-testid="stSidebarNavLink"][aria-current="page"]{background:var(--accent)!important}
[data-testid="stSidebarNavLink"][aria-current="page"] *{color:var(--on-accent)!important;font-weight:700}

/* select box */
[data-baseweb="select"]>div{background:var(--field)!important;border:1px solid var(--border)!important;border-radius:10px!important}
[data-baseweb="select"] *{color:var(--text)!important}
[data-baseweb="popover"] [data-baseweb="menu"],[data-baseweb="popover"] ul{background:var(--card-solid)!important}
[data-baseweb="popover"] li{background:transparent!important;color:var(--text)!important}
[data-baseweb="popover"] li *{color:var(--text)!important}
[data-baseweb="popover"] li:hover,[data-baseweb="popover"] li[aria-selected="true"]{background:var(--hover)!important}

/* mode switch (radio shown as pills) and buttons */
[data-testid="stRadio"] [role="radiogroup"]{gap:.35rem;flex-wrap:nowrap}
[data-testid="stRadio"] label{border:1px solid var(--border);background:var(--field);border-radius:999px;padding:.18rem .8rem;margin:0}
[data-testid="stRadio"] label *{color:var(--text)!important;font-weight:600}
[data-testid="stRadio"] label:has(input:checked){background:var(--accent);border-color:var(--accent)}
[data-testid="stRadio"] label:has(input:checked) *{color:var(--on-accent)!important}
.stButton>button{background:var(--field)!important;color:var(--text)!important;border:1px solid var(--border)!important;border-radius:10px;font-weight:600}
.stButton>button *{color:var(--text)!important}
.stButton>button:hover{border-color:var(--accent)!important}
.stButton>button:hover *{color:var(--accent)!important}

/* text + chat inputs */
[data-baseweb="input"],[data-baseweb="base-input"]{background:var(--field)!important;border-color:var(--border)!important}
[data-testid="stTextInput"] input{background:var(--field)!important;color:var(--text)!important;-webkit-text-fill-color:var(--text)!important}
[data-testid="stBottom"],[data-testid="stBottom"]>div{background:var(--bg-solid)!important}
[data-testid="stChatInput"]{background:transparent!important}
[data-testid="stChatInput"]>div,[data-testid="stChatInput"] [data-baseweb]{background:var(--field)!important;border-color:var(--border)!important}
[data-testid="stChatInput"] textarea{color:var(--text)!important;-webkit-text-fill-color:var(--text)!important;background:transparent!important}
[data-testid="stChatInput"] textarea::placeholder{color:var(--muted)!important;-webkit-text-fill-color:var(--muted)!important;opacity:1}
[data-testid="stChatMessage"]{background:var(--card)!important;border:1px solid var(--border);border-radius:14px}
[data-testid="stChatMessage"] *{color:var(--text)}

/* the map panel is a keyed container so it can be styled like the other cards */
.st-key-mapcard{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:14px 16px 16px;box-shadow:var(--shadow);backdrop-filter:blur(8px)}
.st-key-mapcard [data-testid="stVerticalBlock"]{gap:.6rem}
.st-key-mapcard iframe{border-radius:12px;border:1px solid var(--border);width:100%;display:block}

/* ===== BOGCL components ===== */
.bc,.bc *{box-sizing:border-box}
.bc{color:var(--text)}
.bc-card{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:14px 16px 16px;box-shadow:var(--shadow);backdrop-filter:blur(8px);color:var(--text);min-width:0;overflow:hidden}
.bc-ph{display:flex;align-items:center;justify-content:space-between;gap:10px;margin:0 0 12px;font-size:12px;font-weight:700;letter-spacing:.09em;text-transform:uppercase;color:var(--muted)}
.bc-sub{font-size:12px;color:var(--muted);font-weight:500;letter-spacing:0;text-transform:none}
.bc-grid{display:grid;gap:14px;align-items:stretch}
.bc-r3{grid-template-columns:minmax(0,5fr) minmax(0,7fr)}
.bc-r4{grid-template-columns:minmax(0,3fr) minmax(0,4fr) minmax(0,2.4fr)}
.bc-in{display:grid;gap:12px;min-width:0}
.bc-cq{container-type:inline-size;width:100%}
@container (max-width:1000px){.bc-r3,.bc-r4{grid-template-columns:minmax(0,1fr)}}

.bc-head{display:flex;flex-wrap:wrap;align-items:center;gap:12px 16px}
.bc-brand{display:flex;align-items:center;gap:12px;margin-right:8px}
.bc-logo{width:42px;height:42px;border-radius:12px;display:grid;place-items:center;background:linear-gradient(135deg,var(--accent),var(--accent-2));color:var(--on-accent)}
.bc-title{font-size:22px;font-weight:800;line-height:1.15;letter-spacing:.01em}
.bc-tag{font-size:12.5px;color:var(--muted);margin-top:2px}
.bc-chip{display:inline-flex;align-items:center;gap:8px;padding:8px 14px;border:1px solid var(--border);background:var(--card);border-radius:12px;font-size:14px;font-weight:600;white-space:nowrap}
.bc-chip.bad{border-color:var(--bad);color:var(--bad);background:var(--bad-bg)}
.bc-chip.ok{border-color:var(--good);color:var(--good);background:var(--good-bg)}
.ic{flex:none;vertical-align:middle}

.bc-tiles{display:grid;gap:10px}
.bc-t2{grid-template-columns:repeat(2,minmax(0,1fr))}.bc-t3{grid-template-columns:repeat(3,minmax(0,1fr))}
.bc-t4{grid-template-columns:repeat(4,minmax(0,1fr))}.bc-t6{grid-template-columns:repeat(6,minmax(0,1fr))}
.bc-t7{grid-template-columns:repeat(7,minmax(0,1fr))}
@media (max-width:1500px){.bc-t7{grid-template-columns:repeat(4,minmax(0,1fr))}.bc-t6{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media (max-width:760px){.bc-t4,.bc-t3,.bc-t7,.bc-t6{grid-template-columns:repeat(2,minmax(0,1fr))}}
.bc-tile{background:var(--tile);border:1px solid var(--line);border-radius:12px;padding:11px 12px;min-width:0}
.bc-k{display:flex;align-items:center;gap:6px;font-size:11.5px;color:var(--muted);font-weight:600;letter-spacing:.02em}
.bc-v{font-size:26px;line-height:1.15;font-weight:700;margin-top:6px;font-variant-numeric:tabular-nums;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.bc-v small{font-size:13px;font-weight:600;color:var(--muted);margin-left:4px}
.bc-v.sm{font-size:16.5px}
.bc-strip{display:flex;flex-wrap:wrap;gap:10px}
.bc-strip .bc-tile{flex:1 1 150px}
.bc-strip .bc-v.sm{white-space:normal;overflow-wrap:anywhere;line-height:1.25}
.bc-strip .bc-s{white-space:normal}
.bc-s{font-size:12px;color:var(--muted);margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.bc-c{text-align:center}.bc-c .bc-k{justify-content:center}

.bc-pill{display:inline-flex;align-items:center;gap:5px;padding:2px 10px;border-radius:999px;font-size:12px;font-weight:600;line-height:1.5;white-space:nowrap}
.bc-pill:before{content:"";width:6px;height:6px;border-radius:50%;background:currentColor;display:inline-block}
.bc-p-good{background:var(--good-bg);color:var(--good)}.bc-p-warn{background:var(--warn-bg);color:var(--warn)}
.bc-p-bad{background:var(--bad-bg);color:var(--bad)}.bc-p-info{background:var(--info-bg);color:var(--info)}
.bc-p-mute{background:var(--tile);color:var(--muted)}

.bc-scroll{overflow:auto;border-radius:10px}
table.bc-t{width:100%;border-collapse:collapse;font-size:13px;color:var(--text)}
.bc-t th{position:sticky;top:0;background:var(--card-solid);text-align:left;font-size:11px;letter-spacing:.07em;text-transform:uppercase;color:var(--muted);font-weight:700;padding:8px 10px;border-bottom:1px solid var(--border);white-space:nowrap}
.bc-t td{vertical-align:middle;padding:8px 10px;border-bottom:1px solid var(--line);white-space:nowrap;color:var(--text)}
.bc-t tr:last-child td{border-bottom:0}
.bc-t .n{text-align:right;font-variant-numeric:tabular-nums}
.bc-t tr.sel td{background:var(--hover)}
.bc-dim{color:var(--muted)!important}
.bc-prog{display:flex;align-items:center;gap:8px;min-width:130px}
.bc-bar{flex:1;height:7px;border-radius:99px;background:var(--track);overflow:hidden}
.bc-bar i{display:block;height:100%;border-radius:99px;background:var(--accent)}
.bc-prog span{font-size:12px;font-variant-numeric:tabular-nums;min-width:36px;text-align:right}

.bc-ring{position:relative;margin:0 auto}
.bc-ring svg{display:block}
.bc-ring-c{position:absolute;left:0;right:0;top:50%;transform:translateY(-50%);text-align:center;line-height:1.1}
.bc-ring-v{font-size:26px;font-weight:800;font-variant-numeric:tabular-nums}
.bc-ring-l{font-size:11px;color:var(--muted);margin-top:2px}
.bc-rt{display:flex;flex-direction:column;align-items:center;gap:6px;text-align:center}
.bc-rt .bc-s{white-space:normal}

.bc-kpi{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:flex-end;gap:6px 8px;min-width:0}
.bc-kpi svg{flex:none;align-self:flex-end}
.bc-up{color:var(--good)!important}.bc-down{color:var(--bad)!important}.bc-flat{color:var(--muted)!important}
.bc-delta{font-size:12px;font-weight:700;margin-top:4px}
.bc-delta span{color:var(--muted);font-weight:500}

.bc-legend{display:flex;flex-wrap:wrap;gap:6px 16px;font-size:12px;color:var(--muted);margin-bottom:6px}
.bc-legend i{display:inline-block;width:18px;height:3px;border-radius:2px;margin-right:6px;vertical-align:middle}
.bc-chart{width:100%;height:auto;display:block}
.bc-chart text{fill:var(--muted);font-size:11px}

.bc-plot{position:relative;height:170px;margin-left:34px;border-bottom:1px solid var(--border);
  background:linear-gradient(to bottom,var(--line) 1px,transparent 1px) 0 0/100% 25%}
.bc-ya{position:absolute;left:-34px;width:28px;text-align:right;font-size:10.5px;color:var(--muted);transform:translateY(-50%)}
.bc-bars{position:absolute;inset:0;display:flex;gap:6px;padding:0 4px}
.bc-bcol{position:relative;flex:1;min-width:0}
.bc-bfill{position:absolute;left:50%;bottom:0;width:62%;max-width:34px;transform:translateX(-50%);border-radius:6px 6px 0 0}
.bc-bval{position:absolute;left:0;right:0;text-align:center;font-size:11px;font-weight:700;color:var(--text)}
.bc-blabs{display:flex;gap:6px;margin:6px 4px 0 38px}
.bc-blabs div{flex:1;text-align:center;font-size:10.5px;color:var(--muted);min-width:0;white-space:nowrap}

.bc-al{display:flex;gap:10px;align-items:center;padding:9px 2px;border-bottom:1px solid var(--line)}
.bc-al:last-child{border-bottom:0}
.bc-al-ic{flex:none;width:30px;height:30px;border-radius:50%;display:grid;place-items:center}
.bc-al-b{flex:1;min-width:0}
.bc-al-t{font-size:13.5px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.bc-al-s{font-size:12px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.bc-al-w{font-size:12px;color:var(--muted);white-space:nowrap}

.bc-note{border:1px solid var(--border);background:var(--tile);border-radius:12px;padding:10px 14px;font-size:13.5px;color:var(--text)}
.bc-note.bad{border-color:var(--bad);background:var(--bad-bg)}
.bc-note.warn{border-color:var(--warn);background:var(--warn-bg)}
.bc-foot{margin-top:6px;font-size:12px;color:var(--muted)}
.bc-sql{margin-top:8px}
.bc-sql summary{cursor:pointer;color:var(--accent);font-weight:600;font-size:13px}
.bc-sql pre{margin:8px 0 0;padding:12px 14px;border-radius:10px;background:var(--card-solid);border:1px solid var(--border);color:var(--text);font-size:12.5px;line-height:1.5;overflow:auto;white-space:pre-wrap}
"""
