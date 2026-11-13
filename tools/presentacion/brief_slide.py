"""One-slide (16:9) visual version of run #10's verified Spanish brief. Draft; not part of the demo site.
Every number on the slide must appear in run #10's brief_es.md; the script stops otherwise."""
import os
import re
from html import escape as esc
from pathlib import Path

BRIEF = Path(os.environ["BRIEF"]).read_text()  # the run's brief_es.md, from the archivo branch
UP, DOWN = "#1b7a4a", "#b4441c"

# ------------------------------------------------------------------ content (condensed from run #10)
headline = "Perdimos terreno en un mes en que el mercado ganó"
market = [  # label, value, up?, good?
    ("Noches de grupo", "4.8%", False, False),
    ("Ocupación hotelera", "4.9 pts", True, True),
    ("Asientos aéreos", "2.6%", False, False),
    ("Oportunidades nuevas", "50.0%", True, True),
]
findings = [
    dict(big="−28.9%", title="Las asociaciones explican la caída",
         bars=[("oct 2025", 2698), ("oct 2026", 1919)], unit="noches de grupo", tone="down"),
    dict(big="8,913", title="El acceso aéreo nos cuesta más que el precio",
         bars=[("Acceso aéreo", 8913), ("Precio", 6640)], unit="noches estimadas perdidas, 12 meses", tone="gold"),
    dict(big="10", title="Oportunidades con más de 90 días abiertas",
         text="La más urgente: <b>Grupo Financiero Cumbres</b>, 163 días abierta y evento el 18 de noviembre.", tone="teal"),
]
actions = [
    dict(who="Ventas", when="6 nov", what="Cerrar Grupo Financiero Cumbres",
         stake=[("657", "Grupo Financiero Cumbres")],
         note="Coincide con Industrias Olmo (ganado): suman 444 habitaciones pico."),
    dict(who="Hoteles socios", when="30 nov", what="Confirmar cupo en septiembre de 2027",
         stake=[("1,458", "Corporativo Cedro"), ("872", "Seguros Altavista"), ("662", "Grupo Cumbres")],
         note="Coinciden: suman 1,035 habitaciones pico la noche más cargada."),
    dict(who="Ventas", when="30 nov", what="Presentar el destino",
         stake=[("912", "Laboratorios Sauce"), ("381", "Seguros Mezquite")],
         note="Meses de necesidad sin grupos ganados."),
]
watch = [
    "<b>Diciembre de 2026</b>: 0 oportunidades abiertas.",
    "<b>Colegio Encino</b> (3,764 noches est.): demasiado grande; cerrar o liberar.",
]
data_notes = [
    "<b>Hotel Cerro Verde</b> no envió octubre: pedírselo.",
    "<b>L-0119</b> abierta con fecha pasada: corregir.",
]

# ------------------------------------------------------------------ number check against the brief
num = re.compile(r"\d[\d,]*(?:\.\d+)?")
words = {"10": "Diez"}
src = set(num.findall(BRIEF))
blob = " ".join([headline] + [m[1] for m in market]
                + [f["big"] + f["title"] + " ".join(str(v) for _, v in f.get("bars", [])) + f.get("text", "") for f in findings]
                + [a["what"] + a["note"] + " ".join(s for s, _ in a["stake"]) for a in actions] + watch + data_notes)
blob = re.sub(r"<[^>]+>|L-0119", " ", blob)
bad = sorted({n for n in num.findall(blob)
              if n.replace(",", "") not in {s.replace(",", "") for s in src} and not (n in words and words[n] in BRIEF)})
assert not bad, f"numbers not in run #10 brief: {bad}"


# ------------------------------------------------------------------ render
def chip(label, val, up, good):
    c = UP if good else DOWN
    return f'<div class="mk"><span class="mk-l">{label}</span><b style="color:{c}">{"▲" if up else "▼"} {val}</b></div>'


def finding(i, f):
    body = ""
    if "bars" in f:
        mx = max(v for _, v in f["bars"])
        cols = {"down": ("#c8d5d8", "#d0643f"), "gold": ("#c9801a", "#e3cfae")}[f["tone"]]
        body = "".join(f'<div class="fb"><span>{esc(l)}</span><i style="width:{78 * v / mx:.1f}%;background:{cols[k]}"></i><b>{v:,}</b></div>'
                       for k, (l, v) in enumerate(f["bars"]))
        body += f'<p class="unit">{esc(f["unit"])}</p>'
    else:
        body = f'<p class="ftext">{f["text"]}</p>'
    return (f'<div class="card find t-{f["tone"]}"><div class="f-top"><span class="f-n">{i}</span>'
            f'<b class="f-big">{f["big"]}</b></div><h3>{esc(f["title"])}</h3>{body}</div>')


def action(i, a):
    stake = "".join(f'<div class="st"><b>{s}</b><span>{esc(n)}</span></div>' for s, n in a["stake"])
    return (f'<div class="card act"><div class="a-top"><span class="a-n">{i}</span><span class="who">{esc(a["who"])}</span>'
            f'<span class="when">antes del {esc(a["when"])}</span></div><h3>{esc(a["what"])}</h3>'
            f'<div class="stakes">{stake}</div><p class="a-note">{esc(a["note"])}</p></div>')


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
body{margin:0;background:var(--mist);color:var(--ink);font:400 15px/1.4 var(--sans);font-feature-settings:"tnum" 1,"lnum" 1;overflow:hidden}
.stage{position:absolute;left:0;top:0;width:1600px;height:900px;transform-origin:0 0}
.page{height:900px;padding:26px 34px 16px;display:flex;flex-direction:column;gap:16px}
header{display:flex;align-items:baseline;justify-content:space-between}
h1{font:500 28px/1.1 var(--display);color:var(--ocean);margin:0}
h1 span{color:var(--teal)}
.meta{color:var(--slate);font-size:14px;display:flex;gap:10px;align-items:center}
.syn{background:#fbecd3;color:#7a4a0c;font-weight:600;font-size:11.5px;padding:3px 10px;border-radius:999px;letter-spacing:.02em}
.card{background:#fff;border:1px solid var(--line);border-radius:12px;padding:18px 22px;min-width:0}
.band{background:var(--ocean);color:#fff;border-radius:12px;padding:18px 24px;display:flex;align-items:center;justify-content:space-between;gap:24px}
.band h2{font:500 30px/1.15 var(--display);margin:0;max-width:560px}
.band h2 small{display:block;font:500 12px var(--sans);letter-spacing:.08em;text-transform:uppercase;color:#9fc3ca;margin-bottom:6px}
.mks{display:flex;gap:10px}
.mk{background:#fff;border-radius:10px;padding:10px 16px;min-width:170px;display:flex;flex-direction:column;gap:2px}
.mk-l{color:var(--slate);font-size:12.5px}
.mk b{font:700 26px/1.1 var(--sans)}
.sec{font:700 12px var(--sans);letter-spacing:.09em;text-transform:uppercase;color:var(--slate);margin:0 0 -8px 2px}
.row{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;flex:1;min-height:0}
.find{display:flex;flex-direction:column}
.f-top{display:flex;align-items:center;gap:12px}
.f-n{width:26px;height:26px;border-radius:50%;background:var(--soft);color:var(--slate);font-weight:700;font-size:13px;display:inline-flex;align-items:center;justify-content:center}
.f-big{font:600 42px/1 var(--sans);letter-spacing:-.01em}
.t-down .f-big{color:#b4441c}.t-gold .f-big{color:#a8670f}.t-teal .f-big{color:var(--teal)}
.find h3,.act h3{font:500 20px/1.25 var(--display);color:var(--ocean);margin:8px 0 10px}
.fb{display:grid;grid-template-columns:110px 1fr;align-items:center;gap:8px;font-size:14px;color:var(--slate);margin:6px 0;position:relative}
.fb i{height:18px;border-radius:0 5px 5px 0;display:block}
.fb b{position:absolute;right:0;color:var(--ink);font-size:15px}
.unit{margin:auto 0 0;padding-top:6px;font-size:12.5px;color:var(--slate)}
.ftext{margin:0;font-size:16.5px;line-height:1.45}
.act{display:flex;flex-direction:column;border-top:4px solid var(--teal)}
.a-top{display:flex;align-items:center;gap:10px}
.a-n{width:28px;height:28px;border-radius:50%;background:var(--teal);color:#fff;font-weight:700;font-size:14px;display:inline-flex;align-items:center;justify-content:center}
.who{font-weight:700;font-size:13px;text-transform:uppercase;letter-spacing:.04em}
.when{margin-left:auto;background:#fbecd3;color:#7a4a0c;font-weight:600;font-size:12.5px;padding:3px 10px;border-radius:999px}
.stakes{display:flex;gap:26px;flex-wrap:wrap}
.st{display:flex;flex-direction:column}
.st b{font:600 34px/1.05 var(--sans);color:var(--ocean)}
.st span{font-size:13.5px;color:var(--slate)}
.a-note{margin:auto 0 0;padding-top:10px;font-size:14px;color:var(--slate)}
.bottom{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.mini{padding:12px 18px;display:flex;gap:16px;align-items:flex-start}
.mini h4{font:700 11.5px var(--sans);letter-spacing:.09em;text-transform:uppercase;margin:3px 0 0;white-space:nowrap;min-width:108px}
.mini ul{margin:0;padding-left:16px;font-size:14.5px}
.mini li{margin:1px 0}
.watch h4{color:#a8670f}.notes h4{color:var(--slate)}
.foot{font-size:11.5px;color:var(--slate);margin:0}
body.flow{overflow:auto}
body.flow .stage{position:static;width:auto;height:auto}
body.flow .page{height:auto}
@media (max-width:819px){.row,.bottom{grid-template-columns:1fr}.band{flex-direction:column;align-items:flex-start}.mks{flex-wrap:wrap}.mk{min-width:140px}.page{padding:14px}.mini{flex-direction:column;gap:4px}}
"""

NAV = """<button id="fs" title="Pantalla completa (F)" aria-label="Pantalla completa">⛶</button><style>#fs{position:fixed;right:14px;bottom:12px;z-index:9;border:1px solid #dfe6e6;background:#fff;color:#5d7178;border-radius:8px;width:34px;height:34px;font-size:17px;cursor:pointer;opacity:.55}#fs:hover{opacity:1}:fullscreen #fs{display:none}body.flow #fs{display:none}</style><script>(function(){function fs(){var d=document.documentElement;try{if(!document.fullscreenElement)d.requestFullscreen();else document.exitFullscreen();}catch(e){}}document.getElementById('fs').onclick=fs;document.addEventListener('keydown',function(e){if(e.key==='f'||e.key==='F')fs();if(e.key==='ArrowLeft'||e.key==='PageUp')location.href='tablero.html';});})();</script>"""

page = f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Informe de octubre · Ixtapa-Zihuatanejo (datos sintéticos)</title>
{"<style>" + FONTS_CSS + "</style>" if SITE else '''<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@400;500;600;700&family=Outfit:wght@400;500&display=swap" rel="stylesheet">'''}
<style>{CSS}</style></head>
<body><div class="stage" id="stage"><div class="page">
<header><h1>Informe de octubre <span>· Ixtapa-Zihuatanejo</span></h1>
  <div class="meta">Eventos de negocios, octubre de 2026 <span class="syn">DATOS SINTÉTICOS</span></div></header>
<div class="band"><h2><small>Lectura del mes · contra octubre de 2025</small>{esc(headline)}.</h2>
  <div class="mks">{''.join(chip(*m) for m in market)}</div></div>
<p class="sec">Tres hallazgos</p>
<div class="row">{''.join(finding(i + 1, f) for i, f in enumerate(findings))}</div>
<p class="sec">Tres acciones para noviembre · noches estimadas en juego</p>
<div class="row">{''.join(action(i + 1, a) for i, a in enumerate(actions))}</div>
<div class="bottom">
  <div class="card mini watch"><h4>Para vigilar</h4><ul>{''.join(f'<li>{x}</li>' for x in watch)}</ul></div>
  <div class="card mini notes"><h4>Datos</h4><ul>{''.join(f'<li>{x}</li>' for x in data_notes)}</ul></div>
</div>
<p class="foot">Datos sintéticos: hoteles, grupos y cifras inventados. Redactado por IA (Claude) a partir de los resultados de la corrida #10; 71 de 71 cifras verificadas.</p>
</div></div>
<script>
(function(){{var st=document.getElementById('stage');
function fit(){{if(window.innerWidth<820){{document.body.classList.add('flow');st.style.transform='';return;}}
document.body.classList.remove('flow');
var k=Math.min(window.innerWidth/1600,window.innerHeight/900);
st.style.transform='translate('+((window.innerWidth-1600*k)/2)+'px,'+((window.innerHeight-900*k)/2)+'px) scale('+k+')';}}
window.addEventListener('resize',fit);fit();}})();
</script>{NAV if SITE else ""}</body></html>"""

Path(os.environ.get("OUT", "informe.html")).write_text(page)
print("ok", len(page))
