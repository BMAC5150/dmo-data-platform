# dmo-data-platform

**DATOS SINTÉTICOS.** Prototype of the Small-DMO Business Events Data Platform. Every hotel, organizer and figure in `data/` is invented, except Ixtapa-Zihuatanejo's 6,800 hotel rooms (Datatur).

## What it does
Reads a DMO's Data sheet, hotel form responses and prospect lists; checks the structure; runs six locked business-rule queries; has Claude write a one-page brief in Spanish from the query results only; checks every number in the brief against the results; writes one dated results workbook.

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
| `tools/generate_synthetic.py` | Rebuilds the synthetic data |

## Run locally
    pip install -r requirements.txt
    python tests/test_engine.py
    python src/build_results.py      # writes out/Results 2026-10.xlsx
