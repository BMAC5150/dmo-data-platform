# Vistas para presentar (16:9)

Two one-screen views of run #10 (October 2026, synthetic data), for presenting:

- `tablero.html`: the dashboard on one 16:9 screen. Numbers come from the engine's results on `data/`.
- `informe.html`: run #10's brief on one 16:9 slide. Condensed by hand from run #10's verified `brief_es.md`;
  the build stops if any number on the slide is not in that brief.

Published only by "Publicar sin correr", which adds them to the site with `tools/add_presentation_views.py`.
A full run ("Corrida mensual") does not include them, because the slide belongs to run #10's brief.

Rebuild (from the repo root):

    git show origin/archivo:archivo/2026-10/2026-11-13-corrida-10/brief_es.md > /tmp/brief10.md
    SITE=1 BRIEF=/tmp/brief10.md OUT=presentacion/tablero.html python3 tools/presentacion/compact_dashboard.py
    SITE=1 BRIEF=/tmp/brief10.md OUT=presentacion/informe.html python3 tools/presentacion/brief_slide.py

In either view: F = full screen; arrow keys or a presentation clicker move between the two.
