"""Add the two 16:9 views to a published run's site, inside the Tablero tab.

Usage: python tools/add_presentation_views.py <site_dir>

Copies the four view pages (presentacion/tablero.html, informe.html, tablero-en.html, informe-en.html) into
<site_dir>/presentacion/ and puts a view block at the top of the Tablero tab of <site_dir>/index.html, in each
language. The tab opens on the Dashboard View ("Vista Tablero"); a left-aligned button switches, in place and in
the same browser tab, to the Summary View ("Vista Resumen") and back. F or the ⛶ button = full screen. The tab's
existing detail stays below. Nothing else on the page changes: the brief, Prospección and La corrida are untouched.

Stops with an error, before anything is written, if the page does not have exactly one Tablero tab per language,
or already has the views.
"""
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TAB = '<section class="tab" data-tab="tablero">'
MARK = "vista-16x9"
PAGES = ("tablero.html", "informe.html", "tablero-en.html", "informe-en.html")

LABELS = {
    "es": dict(dash="Vista Tablero", summ="Vista Resumen", fs="Pantalla completa", detail="Detalle del tablero",
               dash_t="Vista Tablero: el tablero en una pantalla", summ_t="Vista Resumen: el informe en una diapositiva",
               suf=""),
    "en": dict(dash="Dashboard View", summ="Summary View", fs="Full screen", detail="Dashboard detail",
               dash_t="Dashboard View: the dashboard on one screen", summ_t="Summary View: the brief on one slide",
               suf="-en"),
}

CSS = f"""<style id="{MARK}-css">
.vista{{position:relative;width:min(calc(100vw - 48px),1560px);left:50%;transform:translateX(-50%);margin:0 0 34px}}
.vista-bar{{display:flex;align-items:center;gap:10px;margin:0 0 10px}}
.vista-btn{{display:inline-flex;align-items:center;gap:7px;background:#00839b;color:#fff;border:0;font:600 14px/1 var(--sans);padding:9px 16px;border-radius:999px;cursor:pointer}}
.vista-btn:hover{{background:#0e2a33}}
.vista-btn[hidden]{{display:none}}
.vista-fs{{margin-left:auto;border:1px solid #dfe6e6;background:#fff;color:#5d7178;border-radius:8px;width:34px;height:34px;font-size:17px;cursor:pointer}}
.vista-fs:hover{{color:#0e2a33;border-color:#b9c6c9}}
.vista-frame{{width:100%;aspect-ratio:16/9;border:1px solid #dfe6e6;border-radius:12px;overflow:hidden;background:#f3f6f5}}
.vista-frame iframe{{width:100%;height:100%;border:0;display:block}}
.vista-frame iframe[hidden]{{display:none}}
.vista-detail{{font:700 12px var(--sans);letter-spacing:.09em;text-transform:uppercase;color:#5d7178;margin:0 0 14px}}
.vista:fullscreen{{width:100vw;height:100vh;left:0;transform:none;margin:0;padding:12px 16px 16px;background:#f3f6f5;display:flex;flex-direction:column}}
.vista:fullscreen .vista-frame{{flex:1;aspect-ratio:auto;border:0;border-radius:0}}
.vista:fullscreen .vista-fs{{display:none}}
@media (max-width:819px){{.vista{{width:100%;left:0;transform:none}}}}
</style>"""

JS = f"""<script id="{MARK}-js">
(function () {{
  var blocks = Array.prototype.slice.call(document.querySelectorAll('.vista'));
  if (!blocks.length) return;
  function frameOf(b) {{ return b.querySelector('iframe[data-v="' + b.dataset.on + '"]'); }}
  function size(b) {{
    var box = b.querySelector('.vista-frame'), f = frameOf(b);
    if (!f || !box.clientWidth) return;
    try {{ f.contentWindow.dispatchEvent(new Event('resize')); }} catch (e) {{}}
    if (box.clientWidth < 820 && document.fullscreenElement !== b) {{
      var d = null; try {{ d = f.contentDocument; }} catch (e) {{}}
      if (d && d.body) {{ box.style.aspectRatio = 'auto'; box.style.height = d.body.scrollHeight + 'px'; }}
    }} else {{ box.style.aspectRatio = ''; box.style.height = ''; }}
  }}
  function show(b, v) {{
    b.dataset.on = v;
    b.querySelectorAll('iframe').forEach(function (f) {{ f.hidden = f.dataset.v !== v; }});
    b.querySelectorAll('.vista-btn').forEach(function (x) {{ x.hidden = x.dataset.go === v; }});
    size(b);
  }}
  function active() {{ return document.querySelector('.lang.on .tab.on .vista'); }}
  function fs(b) {{
    if (!b) return;
    try {{ if (!document.fullscreenElement) b.requestFullscreen(); else document.exitFullscreen(); }} catch (e) {{}}
  }}
  blocks.forEach(function (b) {{
    b.querySelectorAll('.vista-btn').forEach(function (x) {{ x.addEventListener('click', function () {{ show(b, x.dataset.go); }}); }});
    b.querySelector('.vista-fs').addEventListener('click', function () {{ fs(b); }});
    b.querySelectorAll('iframe').forEach(function (f) {{ f.addEventListener('load', function () {{ size(b); }}); }});
    if (window.ResizeObserver) new ResizeObserver(function () {{ size(b); }}).observe(b.querySelector('.vista-frame'));
    show(b, 'tablero');
  }});
  document.addEventListener('keydown', function (e) {{
    if ((e.key !== 'f' && e.key !== 'F') || e.metaKey || e.ctrlKey || e.altKey) return;
    var t = e.target && e.target.tagName;
    if (t === 'INPUT' || t === 'TEXTAREA' || t === 'SELECT') return;
    if (document.fullscreenElement) {{ fs(document.fullscreenElement); return; }}
    fs(active());
  }});
  window.addEventListener('message', function (e) {{
    if (e.origin !== location.origin || !e.data || e.data.vista !== 'fs') return;
    fs(document.fullscreenElement || active());
  }});
  document.addEventListener('fullscreenchange', function () {{ blocks.forEach(size); }});
}})();
</script>"""


def block(lang):
    L = LABELS[lang]
    s = L["suf"]
    return (f'\n  <div class="vista" data-on="tablero">'
            f'<div class="vista-bar">'
            f'<button type="button" class="vista-btn" data-go="informe">▤ {L["summ"]}</button>'
            f'<button type="button" class="vista-btn" data-go="tablero" hidden>▣ {L["dash"]}</button>'
            f'<button type="button" class="vista-fs" title="{L["fs"]} (F)" aria-label="{L["fs"]}">⛶</button></div>'
            f'<div class="vista-frame">'
            f'<iframe data-v="tablero" src="presentacion/tablero{s}.html" title="{L["dash_t"]}" allowfullscreen></iframe>'
            f'<iframe data-v="informe" src="presentacion/informe{s}.html" title="{L["summ_t"]}" allowfullscreen hidden></iframe>'
            f'</div></div>\n  <h3 class="vista-detail">{L["detail"]}</h3>')


def main(site):
    page = site / "index.html"
    html = page.read_text(encoding="utf-8")
    if MARK in html or "vistas-presentacion" in html:
        sys.exit(f"{page} already has the presentation views")
    parts = html.split(TAB)
    if len(parts) != 3:
        sys.exit(f"expected 2 Tablero tabs in {page}, found {len(parts) - 1}")
    langs = []
    for chunk in parts[:2]:
        i = chunk.rfind('<div class="lang" data-lang="')
        if i < 0:
            sys.exit("could not tell which language a Tablero tab belongs to")
        langs.append(chunk[i + 29:i + 31])
    if sorted(langs) != ["en", "es"]:
        sys.exit(f"unexpected languages {langs}")
    if html.count("</head>") != 1 or html.count("</body>") != 1:
        sys.exit("expected one </head> and one </body>")
    missing = [p for p in PAGES if not (REPO / "presentacion" / p).is_file()]
    if missing:
        sys.exit(f"missing view pages: {missing}")
    new = parts[0] + TAB + block(langs[0]) + parts[1] + TAB + block(langs[1]) + parts[2]
    new = new.replace("</head>", CSS + "\n</head>").replace("</body>", JS + "\n</body>")
    out = site / "presentacion"
    out.mkdir(exist_ok=True)
    for name in PAGES:
        shutil.copyfile(REPO / "presentacion" / name, out / name)
    page.write_text(new, encoding="utf-8")
    print(f"Added the Dashboard View / Summary View block to {page} ({', '.join(langs)}) and {len(PAGES)} pages to {out}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
