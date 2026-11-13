"""Add the two 16:9 presentation views to a published run's site.

Usage: python tools/add_presentation_views.py <site_dir>

Copies presentacion/tablero.html and presentacion/informe.html into <site_dir>/presentacion/ and adds a
small "Vistas para presentar" bar at the top of the Tablero tab (Spanish and English) of <site_dir>/index.html.
Nothing else on the page changes. Stops with an error, before anything is written, if the page does not have
exactly one Tablero tab per language or already has the bar.
"""
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TAB = '<section class="tab" data-tab="tablero">'
MARK = "vistas-presentacion"

LABELS = {
    "es": ("Vistas para presentar (16:9)", "Tablero en una pantalla", "Informe en una diapositiva",
           "Se abren en otra pestaña. F: pantalla completa; flechas: pasar de una a otra."),
    "en": ("Presentation views (16:9, in Spanish)", "One-screen dashboard", "One-slide brief",
           "Open in a new tab. F: full screen; arrow keys: switch between them."),
}
CSS = f"""<style id="{MARK}-css">
.{MARK}{{display:flex;align-items:center;gap:10px;flex-wrap:wrap;background:#fff;border:1px solid #cfe3e7;border-radius:12px;padding:12px 16px;margin:0 0 18px}}
.{MARK} b{{font-weight:600;color:#0e2a33;margin-right:4px}}
.{MARK} a{{display:inline-flex;align-items:center;gap:6px;background:#00839b;color:#fff;text-decoration:none;font-weight:600;font-size:14px;padding:7px 14px;border-radius:999px}}
.{MARK} a:hover{{background:#0e2a33}}
.{MARK} small{{color:#5d7178;font-size:12.5px;flex-basis:100%}}
</style>"""


def bar(lang):
    h, a, b, note = LABELS[lang]
    return (f'\n  <div class="{MARK}"><b>{h}</b>'
            f'<a href="presentacion/tablero.html" target="_blank" rel="noopener">▣ {a}</a>'
            f'<a href="presentacion/informe.html" target="_blank" rel="noopener">▤ {b}</a>'
            f'<small>{note}</small></div>')


def main(site):
    page = site / "index.html"
    html = page.read_text(encoding="utf-8")
    if MARK in html:
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
    if html.count("</head>") != 1:
        sys.exit("expected one </head>")
    new = parts[0] + TAB + bar(langs[0]) + parts[1] + TAB + bar(langs[1]) + parts[2]
    new = new.replace("</head>", CSS + "\n</head>")
    out = site / "presentacion"
    out.mkdir(exist_ok=True)
    for name in ("tablero.html", "informe.html"):
        shutil.copyfile(REPO / "presentacion" / name, out / name)
    page.write_text(new, encoding="utf-8")
    print(f"Added presentation views to {page} ({', '.join(langs)}) and {out}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
