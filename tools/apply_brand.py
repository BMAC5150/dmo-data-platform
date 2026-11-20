"""Apply the Ocelo brand to the published site, just before it goes to GitHub Pages.

    python3 tools/apply_brand.py SITE_DIR

Presentation only. It re-skins the pages that are about to be published (dashboard, portal,
targeting guide, 16:9 views, archived runs) and changes no number or word in them:
  - colours: the old "Costa Grande" palette is swapped for the Ocelo palette (ink, gold, cream);
    status colours (green, red, amber, rain blue, synthetic purple) are kept;
  - type: Outfit for everything (one self-hosted variable font, all weights, works offline);
  - mark: the Ocelo lockup in the dashboard header and the portal header, plus the favicon.
The run's own record (results workbook, archived files, saved run artifact) is never touched:
this runs only on the copy that is published. Safe to run twice (pages already done are skipped).
login/ and pitch/ are skipped: they are built in the brand already.
"""
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FONTS = ["outfit-latin-wght-normal.woff2", "outfit-latin-ext-wght-normal.woff2"]
MARKER = 'id="ocelo-brand"'

INK, GOLD, CREAM = "#0F3D3E", "#E2A03F", "#F7F4EE"

# Old palette -> Ocelo. Keys are lower-case 6-digit hex. Anything not listed is left alone.
PALETTE = {
    # brand surfaces and accents
    "#0e2a33": INK,        # ocean: headers, dark cards
    "#133843": "#1A4E4F",  # ocean-2: header gradient
    "#00839b": "#1E5E5B",  # teal accent: bars, buttons, links -> ink family
    "#00677a": "#154846", "#006f84": "#154846",  # teal hover
    "#c9801a": GOLD,       # gold: highlight bars, current month
    "#e8a63c": GOLD,       # horizon gold
    "#5b6fd6": "#8DB6AE",  # third score segment -> soft lagoon
    # cool neutrals -> warm, cream-based
    "#f3f6f5": CREAM,      # page background
    "#f7f9f9": "#FAF8F3",
    "#edf1f1": "#EFEBE3",  # soft line / fill
    "#dfe6e6": "#E4DED3",  # line
    "#c8d5d8": "#D9D2C3",  # last-year bars -> sand
    "#b9c6c9": "#CBC4B5", "#c9d5d6": "#CFC8BA", "#b9cfd4": "#C7D3CF",
    "#14262c": "#132F30",  # body text
    "#5d7178": "#586B69",  # muted text
    # teal tints -> ink tints
    "#e0f0f3": "#E2ECE9", "#e7f4f6": "#E8F0EE", "#eef6f7": "#EEF4F2",
    "#cbe8ee": "#CFE0DC", "#cfe3e7": "#D3E2DE", "#d6e4e6": "#DAE4E1",
    "#cfe0e3": "#D5E2DE", "#a9c3c8": "#A9C4BF", "#9fc3ca": "#A0C2BB",
}
RGBA = [("rgba(14,42,51,", "rgba(15,61,62,"), ("rgba(14, 42, 51,", "rgba(15, 61, 62,")]

MARK_SVG = (
    '<svg viewBox="0 0 100 100" aria-hidden="true">'
    '<circle cx="50" cy="50" r="42" fill="none" stroke="#F7F4EE" stroke-width="12" stroke-linecap="round" '
    'stroke-dasharray="66 22" transform="rotate(45 50 50)"/>'
    '<path d="M22 50 Q50 20 78 50 Q50 80 22 50 Z" fill="#E2A03F"/>'
    '<ellipse cx="50" cy="50" rx="4.5" ry="12" fill="#0F3D3E"/></svg>'
)
LOCKUP_INNER = MARK_SVG + "<b>ocelo</b>"
FAVICON = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E"
    "%3Crect width='100' height='100' rx='22' fill='%230F3D3E'/%3E"
    "%3Ccircle cx='50' cy='50' r='34' fill='none' stroke='%23F7F4EE' stroke-width='10' stroke-linecap='round' "
    "stroke-dasharray='53 18' transform='rotate(45 50 50)'/%3E"
    "%3Cpath d='M27 50 Q50 26 73 50 Q50 74 27 50 Z' fill='%23E2A03F'/%3E"
    "%3Cellipse cx='50' cy='50' rx='3.8' ry='10' fill='%230F3D3E'/%3E%3C/svg%3E"
)

LATIN = ("U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,"
         "U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD")
LATIN_EXT = ("U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+0304,U+0308,U+0329,U+1D00-1DBF,"
             "U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF")


def brand_css(prefix):
    stack = '"Ocelo Outfit","Outfit","Avenir Next","Segoe UI",sans-serif'
    return (
        f'@font-face{{font-family:"Ocelo Outfit";src:url("{prefix}fonts/{FONTS[0]}") format("woff2");'
        f"font-weight:100 900;font-style:normal;font-display:swap;unicode-range:{LATIN}}}"
        f'@font-face{{font-family:"Ocelo Outfit";src:url("{prefix}fonts/{FONTS[1]}") format("woff2");'
        f"font-weight:100 900;font-style:normal;font-display:swap;unicode-range:{LATIN_EXT}}}"
        f":root{{--sans:{stack};--display:{stack}}}"
        f"::selection{{background:{GOLD};color:{INK}}}"
        ".ocelo-lockup{display:inline-flex;align-items:center;gap:10px;color:#F7F4EE;text-decoration:none;vertical-align:middle}"
        ".ocelo-lockup svg{width:30px;height:30px;flex:none}"
        ".ocelo-lockup b{font:600 25px/1 var(--display);letter-spacing:-.035em;color:#F7F4EE}"
        ".hero .wrap>.ocelo-lockup{margin:0 0 30px}"
        ".brand .ocelo-sub{margin-left:14px;padding-left:14px;border-left:1px solid rgba(247,244,238,.25);vertical-align:middle}"
    )


def recolour(text):
    text = re.sub(r"#[0-9a-fA-F]{6}\b", lambda m: PALETTE.get(m.group(0).lower(), m.group(0)), text)
    for old, new in RGBA:
        text = text.replace(old, new)
    return text


def brand_page(path, site):
    text = path.read_text(encoding="utf-8")
    if MARKER in text or "</head>" not in text:
        return None
    rel = path.parent.relative_to(site)
    prefix = "../" * len(rel.parts)
    text = recolour(text)
    head = (f'<link rel="icon" href="{FAVICON}">\n'
            f'<style {MARKER}>{brand_css(prefix)}</style>\n</head>')
    text = text.replace("</head>", head, 1)
    notes = []
    # dashboard header (one per language)
    hero = '<header class="hero"><div class="wrap">'
    if hero in text:
        n = text.count(hero)
        text = text.replace(hero, hero + f'\n  <div class="ocelo-lockup" role="img" aria-label="Ocelo">{LOCKUP_INNER}</div>')
        notes.append(f"lockup x{n}")
    # portal header (React)
    brand = 'h("a", { className: "brand", href: "#inicio" }, L.brand)'
    if brand in text:
        text = text.replace(brand,
            'h("a", { className: "brand", href: "#inicio" }, '
            f'h("span", {{ className: "ocelo-lockup", role: "img", "aria-label": "Ocelo", dangerouslySetInnerHTML: {{ __html: {LOCKUP_INNER!r} }} }}), '
            'h("span", { className: "ocelo-sub" }, L.brand))')
        notes.append("lockup")
    path.write_text(text, encoding="utf-8")
    return notes


def main(site):
    site = Path(site).resolve()
    (site / "fonts").mkdir(exist_ok=True)
    for f in FONTS:
        shutil.copy2(ROOT / "site_assets" / "fonts" / f, site / "fonts" / f)
    shutil.copy2(ROOT / "site_assets" / "fonts" / "OFL-Outfit.txt", site / "fonts" / "OFL-Outfit.txt")
    done = 0
    for p in sorted(site.rglob("*.html")):
        if p.relative_to(site).parts[0] in ("login", "pitch"):
            continue
        notes = brand_page(p, site)
        if notes is not None:
            done += 1
            print(f"  {p.relative_to(site)}" + (f" ({', '.join(notes)})" if notes else ""))
    print(f"Ocelo brand applied to {done} page(s) in {site}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python3 tools/apply_brand.py SITE_DIR")
    main(sys.argv[1])
