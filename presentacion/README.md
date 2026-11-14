# Vista Tablero / Vista Resumen (Dashboard View / Summary View), 16:9

Two one-screen views of run #10 (October 2026, synthetic data), each in Spanish and English:

- `tablero.html`, `tablero-en.html`: Vista Tablero / Dashboard View, the dashboard on one 16:9 screen. Numbers come
  from the engine's results on `data/`; the brief panel condenses run #10's brief and is checked against it.
- `informe.html`, `informe-en.html`: Vista Resumen / Summary View, run #10's brief on one 16:9 slide. Condensed by
  hand from run #10's verified `brief_es.md` / `brief_en.md`; the build stops if any number on the slide is not in
  that brief.

Published only by "Publicar sin correr": `tools/add_presentation_views.py` puts both views at the top of the Tablero
tab, which the site opens on. A left-aligned button switches between them in place, in the same browser tab; the
tab's full detail stays below. F or ⛶ = full screen (the switch button stays available). A full run ("Corrida
mensual") does not include them, because the slide belongs to run #10's brief.

Rebuild (from the repo root):

    for L in es en; do
      git show origin/archivo:archivo/2026-10/2026-11-13-corrida-10/brief_$L.md > /tmp/brief10_$L.md
      S=$([ $L = en ] && echo -en)
      LANG_VIEW=$L SITE=1 BRIEF=/tmp/brief10_$L.md OUT=presentacion/tablero$S.html python3 tools/presentacion/compact_dashboard.py
      LANG_VIEW=$L SITE=1 BRIEF=/tmp/brief10_$L.md OUT=presentacion/informe$S.html python3 tools/presentacion/brief_slide.py
    done
