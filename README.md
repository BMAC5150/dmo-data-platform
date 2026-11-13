# dmo-data-platform

**DATOS SINTÉTICOS.** Prototype of the Small-DMO Business Events Data Platform. Every hotel, organizer and figure in `data/` is invented, except Ixtapa-Zihuatanejo's 6,800 hotel rooms (Datatur).

## What it does
Reads a DMO's Data sheet, hotel form responses and prospect lists; checks the structure; runs six locked business-rule queries; has Claude write a one-page brief in Spanish from the query results only; checks every number in the brief against the results; writes one dated results workbook.

## Demo
- Page: https://bmac5150.github.io/dmo-data-platform/ (synthetic data)
- Run: Actions → "Corrida mensual (demo)" → Run workflow. The run tests the rules, runs the engine, has the Claude API write the brief, checks every number, then publishes the page.

## Layout
| Path | What |
|---|---|
| `data/` | Synthetic input files: copies of the files in the demo Google shared drive |
| `src/schema.json` | Every tab and column the run expects; the run stops if one changes |
| `src/config_ixtapa.json` | The DMO's Drive folders and prospect-list column mapping |
| `src/engine.py` | Structure check, ingestion, the six locked queries, data check |
| `src/build_results.py` | Brief payload, number check, results workbook |
| `brief/brief_es.md` | This month's brief |
| `tests/test_engine.py` | Tests for the locked rules |
| `src/render_site.py` | The demo page (Spanish): La corrida, Tablero, Prospección, Informe |
| `src/brief_api.py` | Claude API call for the brief, with redraft and hold rules |
| `site_assets/fonts/` | Self-hosted Cormorant Garamond and Hanken Grotesk (SIL Open Font License) |
| `tools/generate_synthetic.py` | Rebuilds the synthetic data |

## Run locally
    pip install -r requirements.txt
    python tests/test_engine.py
    python src/build_results.py      # writes out/Results 2026-10.xlsx
