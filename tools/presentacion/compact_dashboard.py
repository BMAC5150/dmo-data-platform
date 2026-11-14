"""Compressed one-screen dashboard ("Vista Tablero" / "Dashboard View"), Spanish or English (LANG=es|en),
light version for a non-analytical audience.

Draft for review: NOT part of the demo site. Every number comes from the locked engine's
results (engine.run on the repo's synthetic data) except the brief panel, which condenses
run #10's verified Spanish brief; its numbers are checked against that brief below.
"""
import os
import re
import sys
from html import escape as esc
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
import engine  # noqa: E402
from render_site import NAMES, MONTHS_SHORT  # noqa: E402

LANG = os.environ.get("LANG_VIEW", "es")
assert LANG in ("es", "en"), LANG
N = NAMES[LANG]
MS = MONTHS_SHORT[LANG]
TX = {
    "es": dict(t_g="Noches de grupo, octubre", t_y="Noches de grupo en el año", t_o="Ocupación hotelera, octubre",
               t_l="Oportunidades nuevas, octubre", t_w="Propuestas ganadas, 12 meses", t_h="Hoteles que reportaron",
               of="de", missing="Falta", all="Todos", rn="noches de grupo", ch_h="Noches de grupo por mes",
               ch_aria="Noches de grupo por mes, {a} y {b}", ch_foot="Meses de baja ocupación: ahí hacen falta grupos.",
               won_t="ganada", lost_t="perdida", nights="noches", est=" estimadas", bx_h="Propuestas decididas en octubre",
               bx_won="ganada", bx_lost="perdidas", bx_foot="Ganamos {w} noches y perdimos unas {l}.",
               pp_h="Prospectos prioritarios", pp_date="Fecha del evento", pp_big="Los más grandes",
               lz_t="noches estimadas", lz_h="Por qué perdemos", lz_r="noches perdidas en 12 meses", rv_h="Quién nos gana",
               br_h="Informe de octubre", br_what="Qué pasó", br_todo="Qué hacer",
               br_foot="Redactado por IA con los resultados del mes. Cifras verificadas.",
               title="Vista Tablero · Ixtapa-Zihuatanejo (datos sintéticos)", h1="Eventos de negocios",
               month="Octubre de 2026", syn="DATOS SINTÉTICOS",
               note="Datos sintéticos para demostración: hoteles, grupos y cifras inventados. Noches de grupo: mismos {c} hoteles en ambos años. Noches perdidas y de prospectos: estimadas.",
               fs="Pantalla completa"),
    "en": dict(t_g="Group room nights, October", t_y="Group room nights, year to date", t_o="Hotel occupancy, October",
               t_l="New leads, October", t_w="Bids won, 12 months", t_h="Hotels that reported",
               of="of", missing="Missing", all="All", rn="group room nights", ch_h="Group room nights by month",
               ch_aria="Group room nights by month, {a} and {b}", ch_foot="Low-occupancy months: that is where groups are needed.",
               won_t="won", lost_t="lost", nights="room nights", est=" estimated", bx_h="Bids decided in October",
               bx_won="won", bx_lost="lost", bx_foot="We won {w} room nights and lost about {l}.",
               pp_h="Priority prospects", pp_date="Event date", pp_big="The largest",
               lz_t="estimated room nights", lz_h="Why we lose", lz_r="room nights lost, last 12 months", rv_h="Who beats us",
               br_h="October brief", br_what="What happened", br_todo="What to do",
               br_foot="Drafted by AI from the month's results. Figures verified.",
               title="Dashboard View · Ixtapa-Zihuatanejo (synthetic data)", h1="Business events",
               month="October 2026", syn="SYNTHETIC DATA",
               note="Synthetic demonstration data: hotels, groups and figures are invented. Group room nights: the same {c} hotels in both years. Lost and prospect room nights: estimated.",
               fs="Full screen"),
}[LANG]
R = engine.run(REPO / "data/Data (SINTETICO).xlsx", REPO / "data/Hotel responses (SINTETICO).xlsx", REPO / "data/imports")
S, t, tot, ins = R["S"], R["trend"], R["tot"], R["insights"]
rm = S["report_month"]
ly = rm - 12
sc = {r["metric"]: r for r in R["scorecard"]}

TEAL, GOLD, PALE = "#00839b", "#c9801a", "#c8d5d8"
UP, DOWN = "#1b7a4a", "#b4441c"


def n0(x):
    return f"{x:,.0f}"


def delta(chg, kind):
    txt = f"{abs(chg):.1f} pts" if kind == "points" else f"{abs(chg) * 100:.1f}%"
    up = chg >= 0
    return f'<span class="d" style="color:{UP if up else DOWN}">{"▲" if up else "▼"} {txt}</span>'


# ------------------------------------------------------------------ KPI tiles: number + one short line
g, y, o, lr = sc["group_room_nights_month"], sc["group_room_nights_ytd"], sc["hotel_occupancy_month"], sc["leads_received_month"]
n_hotels, n_comp = len(R["hotels"]), t["comparable_hotels"]
missing = t["excluded_hotels"]
vs = f"vs {ly.year}"
tiles = [
    (TX["t_g"], n0(g["value"]), f'{delta(g["change"], "pct")} {vs}'),
    (TX["t_y"], n0(y["value"]), f'{delta(y["change"], "pct")} {vs}'),
    (TX["t_o"], f'{o["value"]:.1f}%', f'{delta(o["change"], "points")} {vs}'),
    (TX["t_l"], n0(lr["value"]), f'{delta(lr["change"], "pct")} {vs}'),
    (TX["t_w"], f'{tot["win_rate"] * 100:.0f}%', f'{tot["won"]} {TX["of"]} {tot["decided"]}'),
    (TX["t_h"], f"{n_comp} {TX['of']} {n_hotels}",
     f'<span class="d" style="color:{DOWN}">{TX["missing"]} {esc(missing[0].replace("Hotel ", ""))}</span>' if missing else TX["all"]),
]
kpi_html = "".join(f'<div class="card kpi"><span class="k-l">{esc(a)}</span><b class="k-v">{b}</b><span class="k-s">{c}</span></div>'
                   for a, b, c in tiles)

# ------------------------------------------------------------------ monthly bars, 2025 vs 2026
mon = t["monthly"].copy()
val = {pd.Period(m, "M"): v for m, v in zip(mon["Month"], mon.iloc[:, 1])}
need = set(S["need_months"])
W, H, top, base = 760, 232, 16, 198
vmax = 11000
gw = (W - 10) / 12
bw = (gw - 8) / 2
parts = []
for i in range(12):
    x0 = 10 + i * gw + 3
    for j, yr in enumerate((ly.year, rm.year)):
        p = pd.Period(f"{yr}-{i + 1:02d}", "M")
        v = val.get(p)
        if v is None:
            continue
        h = (base - top) * v / vmax
        x = x0 + j * (bw + 2)
        col = PALE if yr == ly.year else (GOLD if p == rm else TEAL)
        parts.append(f'<g class="bar"><title>{MS[i]} {yr}: {n0(v)} {TX["rn"]}</title>'
                     f'<path d="M{x:.1f},{base} v{-(h - 3):.1f} q0,-3 3,-3 h{bw - 6:.1f} q3,0 3,3 v{h - 3:.1f} z" fill="{col}"/>'
                     f'<rect x="{x - 1:.1f}" y="{top}" width="{bw + 2:.1f}" height="{base - top}" fill="transparent"/></g>')
    cx = x0 + bw + 1
    m = i + 1
    if m in need:
        parts.append(f'<rect x="{x0 - 2:.1f}" y="{base + 4}" width="{2 * bw + 6:.1f}" height="22" rx="11" fill="#fbecd3"/>')
    parts.append(f'<text x="{cx:.1f}" y="{base + 19}" text-anchor="middle" class="ax{" need" if m in need else ""}">{MS[i][0].upper()}</text>')
# label the reported month
p_now = rm
v_now = val[p_now]
x_now = 10 + (p_now.month - 1) * gw + 3 + bw + 2 + bw / 2
y_now = base - (base - top) * v_now / vmax
parts.append(f'<text x="{x_now:.1f}" y="{y_now - 6:.1f}" text-anchor="middle" class="vl">{n0(v_now)}</text>')
chart_svg = (f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{TX['ch_aria'].format(a=ly.year, b=rm.year)}">'
             f'<line x1="6" x2="{W}" y1="{base}" y2="{base}" class="base"/>{"".join(parts)}</svg>')
chart_html = f"""<div class="card">
  <div class="hd"><h2>{TX['ch_h']}</h2>
    <span class="lg"><i style="background:{TEAL}"></i>{rm.year}<i style="background:{PALE}"></i>{ly.year}</span></div>
  {chart_svg}
  <p class="foot"><span class="chip-need">{MS[4][0].upper()}</span> {TX['ch_foot']}</p>
</div>"""

# ------------------------------------------------------------------ October decisions: one bar per bid
leads = pd.read_excel(REPO / "data/Data (SINTETICO).xlsx", sheet_name="Leads")
leads["Est"] = (leads["Peak rooms"] * (pd.to_datetime(leads["End date"]) - pd.to_datetime(leads["Start date"])).dt.days).fillna(0).astype(int)
dec = leads[leads.Status.isin(["Won", "Lost"]) & (pd.to_datetime(leads["Decision date"]).dt.to_period("M") == rm)].copy()
dec["RN"] = dec.apply(lambda r: int(r["Actual room nights"]) if r.Status == "Won" else int(r.Est), axis=1)
dec = dec.sort_values(["Status", "RN"], ascending=[False, False])  # won first, then biggest losses
mx = dec.RN.max()
rows = "".join(
    f'<div class="bid" title="{esc(r.Organizer)}: {TX["won_t"] if r.Status == "Won" else TX["lost_t"]}, {n0(r.RN)} {TX["nights"]}'
    f'{"" if r.Status == "Won" else TX["est"]}"><span class="ic {"w" if r.Status == "Won" else "l"}">{"✓" if r.Status == "Won" else "✕"}</span>'
    f'<span class="bid-n">{esc(r.Organizer)}</span><span class="bid-t"><i class="{"w" if r.Status == "Won" else "l"}" style="width:{100 * r.RN / mx:.1f}%"></i></span>'
    f'<span class="bid-v">{n0(r.RN)}</span></div>' for _, r in dec.iterrows())
n_won_m = int((dec.Status == "Won").sum())
won_rn = int(dec.loc[dec.Status == "Won", "RN"].sum())
lost_rn = int(dec.loc[dec.Status == "Lost", "RN"].sum())
box_html = f"""<div class="card">
  <div class="hd"><h2>{TX['bx_h']}</h2>
    <span class="score"><b class="w">{n_won_m}</b> {TX['bx_won']} <b class="l">{len(dec) - n_won_m}</b> {TX['bx_lost']}</span></div>
  {rows}
  <p class="foot">{TX['bx_foot'].format(w=n0(won_rn), l=n0(lost_rn))}</p>
</div>"""

# ------------------------------------------------------------------ priority prospects by sector x month
f = R["fit"]
prio = f[f.Priority == "Yes"].copy()
prio["P"] = pd.to_datetime(prio["Start date"]).dt.to_period("M")
months = [rm + k for k in range(1, 14)]
strip_hd = "".join(f'<span class="{"need" if p.month in need else ""}">{MS[p.month - 1][0].upper()}</span>' for p in months)
lt_rows = []
for sector, gdf in sorted(prio.groupby("Sector"), key=lambda kv: (-len(kv[1]), -kv[1]["Est. room nights"].sum())):
    cells = ""
    for p in months:
        k = int((gdf.P == p).sum())
        cells += f'<span class="{"on" if k else ""}" title="{MS[p.month - 1]} {p.year}: {k}">{k if k else ""}</span>'
    lt_rows.append(f'<div class="lt-row"><div class="lt-name">{esc(N["sector"].get(sector, sector))}</div>'
                   f'<div class="strip">{cells}</div></div>')
pp = ins["priority_pipeline"]
top = pp["top_5_by_room_nights"][:3]
top_html = "".join(
    f'<li><b>{esc(r["Organizer"])}</b><span>{MS[pd.Timestamp(r["Start date"]).month - 1]} {pd.Timestamp(r["Start date"]).year}</span>'
    f'<em>{n0(r["Est. room nights"])} {TX["nights"]}</em></li>' for r in top)
lt_html = f"""<div class="card">
  <div class="hd"><h2>{TX['pp_h']}</h2><span class="big">{pp['leads']}</span></div>
  <div class="lt-row lt-head"><div class="lt-name">{TX['pp_date']}</div><div class="strip hdr">{strip_hd}</div></div>
  <div class="lt-row lt-yr"><div></div><div class="strip yrs"><span>{months[0].year}</span><span>{months[-1].year}</span></div></div>
  {''.join(lt_rows)}
  <h3 class="sub">{TX['pp_big']}</h3>
  <ol class="top">{top_html}</ol>
</div>"""

# ------------------------------------------------------------------ why we lose: top reasons by room nights, rest folded
lost = ins["lost_last_12_months"]
br = lost["by_reason"]
TOPN = 4
shown = br[:TOPN]
rest = sum(r["room_nights_lost"] for r in br[TOPN:])
items = [(N["loss"].get(r["Loss reason"], r["Loss reason"]), r["room_nights_lost"]) for r in shown] 
mx = max(v for _, v in items)
lose_rows = "".join(
    f'<div class="lz" title="{esc(lbl)}: {n0(v)} {TX["lz_t"]}"><span class="lz-l">{esc(lbl)}</span>'
    f'<span class="lz-t"><i class="{"o" if lbl == "Otros" else ""}" style="width:{100 * v / mx:.1f}%"></i></span><span class="lz-v">{n0(v)}</span></div>'
    for lbl, v in items)
lt_ = R["lost_to"]
rivals = "".join(f'<span><b>{esc(r["Lost to"])}</b> {r["Leads lost"]}</span>'
                 for _, r in lt_[lt_["Lost to"] != "Other"].head(3).iterrows())
lose_html = f"""<div class="card">
  <div class="hd"><h2>{TX['lz_h']}</h2><span class="hd-r">{TX['lz_r']}</span></div>
  {lose_rows}
  <h3 class="sub">{TX['rv_h']}</h3>
  <div class="rivals">{rivals}</div>
</div>"""

# ------------------------------------------------------------------ brief (condensed from run #10's verified brief)
BRIEF_SRC = Path(os.environ["BRIEF"]).read_text()  # the run's brief_es.md, from the archivo branch
what, todo = {
    "es": ([
        "Las asociaciones cayeron 28.9%.",
        "El acceso aéreo nos cuesta más noches que el precio.",
    ], [
        ("Ventas", "6 nov", "Cerrar Grupo Financiero Cumbres (657 noches)."),
        ("Hoteles socios", "30 nov", "Confirmar cupo en septiembre de 2027 para Cedro, Altavista y Grupo Cumbres."),
        ("Ventas", "30 nov", "Presentar el destino a Laboratorios Sauce y Seguros Mezquite."),
    ]),
    "en": ([
        "Associations fell 28.9%.",
        "Air access costs us more room nights than price.",
    ], [
        ("Sales", "Nov 6", "Close Grupo Financiero Cumbres (657 room nights)."),
        ("Partner hotels", "Nov 30", "Confirm September 2027 space for Cedro, Altavista and Grupo Cumbres."),
        ("Sales", "Nov 30", "Pitch Laboratorios Sauce and Seguros Mezquite."),
    ]),
}[LANG]
num = re.compile(r"\d[\d,]*(?:\.\d+)?")
src_nums = {x.replace(",", "") for x in num.findall(BRIEF_SRC)}  # commas ignored ("30," in "November 30, 2026")
check_text = what + [f"{a} {b} {c}" for a, b, c in todo]
bad = [n for line in check_text for n in num.findall(line) if n.replace(",", "") not in src_nums]
assert not bad, f"brief panel numbers not in run #10 brief: {bad}"
todo_html = "".join(f'<li><span class="who">{esc(a)} · {esc(b)}</span>{esc(c)}</li>' for a, b, c in todo)
brief_html = f"""<div class="card brief">
  <div class="hd"><h2>{TX['br_h']}</h2></div>
  <h3>{TX['br_what']}</h3><ul class="what">{''.join(f'<li>{esc(x)}</li>' for x in what)}</ul>
  <h3>{TX['br_todo']}</h3><ol class="todo">{todo_html}</ol>
  <p class="foot">{TX['br_foot']}</p>
</div>"""

# ------------------------------------------------------------------ page
SITE = os.environ.get("SITE") == "1"  # site build: self-hosted fonts, keyboard nav, fullscreen button
FONTS_CSS = """
@font-face{font-family:"Outfit";font-weight:400;font-display:swap;src:url("../fonts/outfit-latin-400-normal.woff2") format("woff2")}
@font-face{font-family:"Outfit";font-weight:500;font-display:swap;src:url("../fonts/outfit-latin-500-normal.woff2") format("woff2")}
@font-face{font-family:"Hanken Grotesk";font-weight:400;font-display:swap;src:url("../fonts/hanken-grotesk-latin-400-normal.woff2") format("woff2")}
@font-face{font-family:"Hanken Grotesk";font-weight:500;font-display:swap;src:url("../fonts/hanken-grotesk-latin-500-normal.woff2") format("woff2")}
@font-face{font-family:"Hanken Grotesk";font-weight:600;font-display:swap;src:url("../fonts/hanken-grotesk-latin-600-normal.woff2") format("woff2")}
@font-face{font-family:"Hanken Grotesk";font-weight:700;font-display:swap;src:url("../fonts/hanken-grotesk-latin-700-normal.woff2") format("woff2")}
"""

CSS = """
:root{--ocean:#0e2a33;--teal:#00839b;--gold:#c9801a;--mist:#f3f6f5;--ink:#14262c;--slate:#5d7178;--line:#dfe6e6;--soft:#edf1f1;
--display:"Outfit","Avenir Next","Segoe UI",sans-serif;--sans:"Hanken Grotesk","Helvetica Neue",Arial,sans-serif}
*{box-sizing:border-box}
html,body{height:100%}
body{margin:0;background:var(--mist);overflow:hidden;color:var(--ink);font:400 14px/1.45 var(--sans);font-feature-settings:"tnum" 1,"lnum" 1}
.stage{position:absolute;left:0;top:0;width:1600px;height:900px;transform-origin:0 0}
.page{height:900px;padding:24px 32px 14px;display:flex;flex-direction:column}
.page>.grid.r2,.page>.grid.r3{flex:1;min-height:0}
.card{overflow:hidden}
header{display:flex;align-items:baseline;justify-content:space-between;gap:12px;margin-bottom:16px;flex-wrap:wrap}
h1{font:500 26px/1.1 var(--display);color:var(--ocean);margin:0;letter-spacing:-.01em}
h1 span{color:var(--teal)}
.meta{color:var(--slate);font-size:14px;display:flex;gap:10px;align-items:center}
.syn{background:#fbecd3;color:#7a4a0c;font-weight:600;font-size:11.5px;padding:3px 10px;border-radius:999px;letter-spacing:.02em}
.grid{display:grid;gap:16px}
.kpis{grid-template-columns:repeat(6,1fr)}
.r2{grid-template-columns:1fr 1fr;margin-top:16px;flex:1.05 !important}
.r3{grid-template-columns:1fr 1fr 1fr;margin-top:16px;flex:1.25 !important}
.card{background:#fff;border:1px solid var(--line);border-radius:12px;padding:16px 18px;display:flex;flex-direction:column;min-width:0}
.kpi{gap:4px;padding:14px 16px}
.k-l{color:var(--slate);font-size:13px;line-height:1.3}
.k-v{font:600 30px/1.05 var(--sans);color:var(--ocean);letter-spacing:-.01em}
.k-s{font-size:13px;color:var(--slate)}
.d{font-weight:600}
.hd{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:12px;flex-wrap:wrap}
h2{font:500 17px/1.2 var(--display);margin:0;color:var(--ocean)}
.hd-r{font-size:12.5px;color:var(--slate)}
.big{font:600 26px/1 var(--sans);color:var(--teal)}
.lg{font-size:12.5px;color:var(--slate);display:flex;align-items:center;gap:5px}
.lg i{width:11px;height:11px;border-radius:3px;display:inline-block;margin-left:8px}
svg{width:100%;height:auto;display:block}
svg .base{stroke:#b9c6c9;stroke-width:1}
svg .ax{fill:var(--slate);font:500 13px var(--sans)}
svg .ax.need{fill:#7a4a0c;font-weight:700}
svg .vl{fill:var(--ink);font:700 13px var(--sans)}
svg .bar:hover path{opacity:.8}
.foot{margin:auto 0 0;padding-top:12px;font-size:12.5px;color:var(--slate)}
.chip-need{display:inline-block;background:#fbecd3;color:#7a4a0c;font-weight:700;font-size:11px;border-radius:999px;padding:1px 7px;margin-right:4px}
.score{font-size:13px;color:var(--slate);display:flex;align-items:center;gap:6px}
.score b{font:700 15px var(--sans);width:26px;height:26px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;color:#fff}
.score b.w{background:#2e9e64}.score b.l{background:#d0643f;margin-left:8px}
.bid{display:grid;grid-template-columns:22px minmax(220px,1fr) 1.4fr 56px;gap:12px;align-items:center;padding:2px 0;font-size:13.5px}
.bid-head{font-size:11.5px;color:var(--slate);padding:0}
.ic{width:20px;height:20px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;color:#fff}
.ic.w{background:#2e9e64}.ic.l{background:#d0643f}
.bid-n{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.bid-t{height:12px;position:relative}
.bid-t i{position:absolute;inset:0 auto 0 0;border-radius:0 4px 4px 0}
.bid-t i.w{background:#2e9e64}.bid-t i.l{background:#e8a48a}
.bid-v{text-align:right;font-weight:600}
.bid-head .bid-v{font-weight:400}
.lt-row{display:grid;grid-template-columns:minmax(130px,1fr) minmax(0,2fr);gap:10px;align-items:center;padding:5px 0}
.lt-head{font-size:11.5px;color:var(--slate);padding-bottom:0}
.lt-yr{padding:0 0 4px}
.lt-name{font-weight:600;font-size:13.5px}
.lt-head .lt-name{font-weight:400;font-size:11.5px}
.strip{display:grid;grid-template-columns:repeat(13,1fr);gap:3px}
.strip span{height:22px;border-radius:5px;background:var(--soft);font-size:11.5px;font-weight:700;color:#fff;display:flex;align-items:center;justify-content:center}
.strip span.on{background:var(--teal)}
.strip.hdr span{background:none;color:var(--slate);font-weight:500;height:auto}
.strip.hdr span.need{color:#7a4a0c;font-weight:700;background:#fbecd3;border-radius:999px}
.strip.yrs{display:flex;justify-content:space-between}
.strip.yrs span{background:none;color:var(--slate);font-size:10.5px;font-weight:500;height:auto}
h3.sub{font:700 11px var(--sans);letter-spacing:.08em;text-transform:uppercase;color:var(--slate);margin:12px 0 6px}
ol.top{list-style:none;margin:0;padding:0}
ol.top li{display:grid;grid-template-columns:1fr auto auto;gap:10px;align-items:baseline;padding:4px 0;font-size:13.5px}
ol.top span{color:var(--slate);font-size:12.5px}
ol.top em{font-style:normal;font-weight:600}
.lz{display:grid;grid-template-columns:140px 1fr 52px;gap:10px;align-items:center;padding:6px 0;font-size:13.5px}
.lz-t{height:14px;position:relative}
.lz-t i{position:absolute;inset:0 auto 0 0;background:var(--gold);border-radius:0 5px 5px 0}
.lz-t i.o{background:#e3d5bf}
.lz-v{text-align:right;font-weight:600}
.rivals{display:flex;flex-wrap:wrap;gap:8px}
.rivals span{background:var(--soft);border-radius:999px;padding:4px 12px;font-size:13px;color:var(--slate)}
.rivals b{color:var(--ink);font-weight:600}
.brief{background:#eef6f7;border-color:#cfe3e7}
.brief h3{font:700 11px var(--sans);letter-spacing:.08em;text-transform:uppercase;color:var(--teal);margin:2px 0 6px}
ul.what{margin:0 0 14px;padding-left:18px}
ul.what li{margin:0 0 4px;font-size:14px}
ol.todo{list-style:none;margin:0;padding:0;counter-reset:a}
ol.todo li{counter-increment:a;position:relative;padding:0 0 10px 34px;font-size:14px;line-height:1.35}
ol.todo li::before{content:counter(a);position:absolute;left:0;top:1px;width:24px;height:24px;border-radius:50%;background:var(--teal);color:#fff;font-weight:700;font-size:12.5px;display:flex;align-items:center;justify-content:center}
.who{display:block;font-size:11.5px;font-weight:700;color:var(--slate);text-transform:uppercase;letter-spacing:.04em}
.note{margin:10px 2px 0;font-size:11.5px;color:var(--slate)}
body.flow{overflow:auto}
body.flow .stage{position:static;width:auto;height:auto}
body.flow .page{height:auto;display:block}
body.flow .card{overflow:visible}
@media (max-width:819px){.kpis{grid-template-columns:repeat(2,1fr)}.r2,.r3{grid-template-columns:1fr}.page{padding:14px}.kpis{grid-template-columns:repeat(2,1fr)}.page{padding:14px}.bid{grid-template-columns:22px minmax(110px,1.4fr) 1fr 46px;gap:8px}.lt-row{grid-template-columns:96px minmax(0,2fr)}.lz{grid-template-columns:112px 1fr 48px}}
"""

from _nav import NAV  # noqa: E402  (shared full-screen control)

page = f"""<!DOCTYPE html>
<html lang="{LANG}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{TX['title']}</title>
{"<style>" + FONTS_CSS + "</style>" if SITE else '''<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@400;500;600;700&family=Outfit:wght@400;500&display=swap" rel="stylesheet">'''}
<style>{CSS}</style></head>
<body><div class="stage" id="stage"><div class="page">
<header><h1>{TX['h1']} <span>· Ixtapa-Zihuatanejo</span></h1>
  <div class="meta">{TX['month']} <span class="syn">{TX['syn']}</span></div></header>
<div class="grid kpis">{kpi_html}</div>
<div class="grid r2">{chart_html}{box_html}</div>
<div class="grid r3">{lt_html}{lose_html}{brief_html}</div>
<p class="note">{TX['note'].format(c=n_comp)}</p>
</div></div>
<script>
(function(){{var st=document.getElementById('stage');
function fit(){{if(window.innerWidth<820){{document.body.classList.add('flow');st.style.transform='';return;}}
document.body.classList.remove('flow');
var k=Math.min(window.innerWidth/1600,window.innerHeight/900);
st.style.transform='translate('+((window.innerWidth-1600*k)/2)+'px,'+((window.innerHeight-900*k)/2)+'px) scale('+k+')';}}
window.addEventListener('resize',fit);fit();}})();
</script>{NAV.replace("%%FS%%", TX["fs"]) if SITE else ""}</body></html>"""

out = Path(os.environ.get("OUT", "tablero.html"))
out.write_text(page)
print("wrote", out, len(page), "bytes")
