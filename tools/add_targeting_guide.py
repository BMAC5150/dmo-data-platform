"""Add the Targeting Guide tab to a published run's site.

Usage: python tools/add_targeting_guide.py <site_dir>

Copies guia/index.html and guia/vendor/ into <site_dir>/guia/ and adds a fifth tab, "Guía de prospección" /
"Targeting guide", after Prospección in each language. The tab shows the guide in a same-origin iframe that
grows to the guide's height; the guide follows the page's language. Nothing else on the page changes: the
dashboard, the brief, Prospección and La corrida are untouched.

Unlike the rest of the demo, the guide uses real public data for Ixtapa-Zihuatanejo (Datatur, AFAC, OAG,
hotel association, weather normals), plus labelled estimates and synthetic examples; it says so at the top.

Stops with an error, before anything is written, if the page does not have exactly one Prospección tab button
and one main block per language, or already has the guide.
"""
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MARK = "guia-prospeccion"
BTN = '<button role="tab" data-t="prospeccion">'
MAIN_END = "</div></main>"
TABS_JS = "var TABS = ['corrida', 'tablero', 'prospeccion', 'informe'];"
LABELS = {"es": ("Guía de prospección", "Guía de prospección de eventos de negocios"),
          "en": ("Targeting guide", "Business events targeting guide")}

CSS = f"""<style id="{MARK}-css">
.guia-frame{{width:100%;height:2400px;border:0;display:block;background:transparent}}
</style>"""

JS = f"""<script id="{MARK}-js">
(function () {{
  window.addEventListener('message', function (e) {{
    if (e.origin !== location.origin || !e.data || e.data.guia !== 'h') return;
    document.querySelectorAll('.guia-frame').forEach(function (f) {{
      if (f.contentWindow === e.source && e.data.h > 0) f.style.height = Math.ceil(e.data.h) + 'px';
    }});
  }});
}})();
</script>"""


def main(site):
    page = site / "index.html"
    html = page.read_text(encoding="utf-8")
    if MARK in html or 'data-tab="guia"' in html:
        sys.exit(f"{page} already has the targeting guide")
    if html.count(TABS_JS) != 1:
        sys.exit("could not find the page's tab list in its script")
    if html.count("</head>") != 1 or html.count("</body>") != 1:
        sys.exit("expected one </head> and one </body>")
    for name in ("index.html", "vendor/react.production.min.js", "vendor/react-dom.production.min.js", "vendor/htm.umd.js"):
        if not (REPO / "guia" / name).is_file():
            sys.exit(f"missing guia/{name}")

    # one language block at a time, in page order
    chunks = html.split('<div class="lang" data-lang="')
    if len(chunks) != 3:
        sys.exit(f"expected 2 language blocks, found {len(chunks) - 1}")
    out = [chunks[0]]
    langs = []
    for chunk in chunks[1:]:
        lang = chunk[:2]
        if lang not in LABELS:
            sys.exit(f"unexpected language {lang!r}")
        if chunk.count(BTN) != 1 or chunk.count(MAIN_END) != 1:
            sys.exit(f"expected one Prospección tab and one main block in the {lang} page")
        tab, title = LABELS[lang]
        i = chunk.index(BTN)
        j = chunk.index("</button>", i) + len("</button>")
        chunk = chunk[:j] + f'<button role="tab" data-t="guia">{tab}</button>' + chunk[j:]
        section = (f'\n<section class="tab" data-tab="guia">'
                   f'<iframe class="guia-frame" src="guia/index.html?lang={lang}" title="{title}" loading="lazy"></iframe>'
                   f'</section>')
        chunk = chunk.replace(MAIN_END, section + MAIN_END)
        out.append(chunk)
        langs.append(lang)
    if sorted(langs) != ["en", "es"]:
        sys.exit(f"unexpected languages {langs}")

    new = '<div class="lang" data-lang="'.join(out)
    new = new.replace(TABS_JS, "var TABS = ['corrida', 'tablero', 'prospeccion', 'guia', 'informe'];")
    new = new.replace("</head>", CSS + "\n</head>").replace("</body>", JS + "\n</body>")

    dest = site / "guia"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(REPO / "guia", dest)
    page.write_text(new, encoding="utf-8")
    print(f"Added the Targeting Guide tab to {page} ({', '.join(langs)}) and copied guia/ to {dest}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
