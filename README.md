# StreamVault Licensing

ML title-licensing pipeline. Kwame Boateng has $14M to commit at the board's licensing review: should it go to franchise bundles or standalone hits, and what should he negotiate for? This repo ingests a list of TMDB movie ids, fetches details + credits, validates the join, and produces a shortlist, a talent read, a deal note, and a one-page client memo.

## Problem being solved
Decide whether franchise bundles or standalone hits are the better licensing bet, and produce defensible numbers (hit rate, adjusted rating, ROI) plus a ranked shortlist. Every metric is a proxy — there is no licensing cost and no viewing data — so the pipeline also documents what could not be verified.

## How the pieces connect
```
data/input/id_list.csv  (the only file Adjoa swaps each cycle)
        |
        v
src/fetch.py   -> data/raw/{details,credits}/{id}.json   (cached, resumable, rate-limited)
        |
        v
src/tidy.py    -> data/processed/{films,credits,analysis_table}.parquet
        |
        v
src/checks.py  -> reconciliation + join-integrity assertions (fail loudly)
        |
        v
src/metrics.py + src/analysis.py  -> outputs/tables/{window_comparison,bundle_summary,shortlist,sensitivity}.csv
src/talent.py  -> outputs/tables/talent_read.csv
src/report.py  -> outputs/run_log.txt + outputs/data_quality_report.txt
        |
        v
docs/  -> 01_data_diagnosis.md, 02_decision_notes.md, 03_client_memo.md, 04_improvement.md
```

- `config.yaml` holds every tunable number (windows, hit thresholds, min votes, min films per director/actor, rate limit, retries). Change a decision there, not in code.
- `notebooks/00_first_look.ipynb` is exploratory only; nothing in the pipeline depends on it.
- `docs/adr/` holds Architecture Decision Records (field selection, missing-film handling).
- `tests/test_integrity.py` guards row counts, no dropped/duplicated films, ledger reconciliation.

## Reproduce on your own machine

1. Clone and create a venv (Python 3.13 recommended — 3.15 has no wheels for pandas/pyarrow):
   ```bash
   python -m venv .venv
   .venv\Scripts\activate          # Windows
   # source .venv/bin/activate     # macOS/Linux
   pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and add your TMDB API key:
   ```bash
   copy .env.example .env         # Windows
   # cp .env.example .env         # macOS/Linux
   ```
3. Put your ids in `data/input/id_list.csv` (one `tmdb_id` per row). This is the only file you swap each cycle.
4. Run the whole pipeline:
   ```bash
   make all                       # or: python run_all.py
   ```
   This runs fetch -> tidy -> checks -> analysis -> talent -> report and writes `data/processed/`, `outputs/`, and refreshes `docs/`.

5. Verify:
   ```bash
   .venv\Scripts\python.exe -m pytest tests/ -q
   ```
   Expected: 6 passed.

## Key results (this cycle)
- 126 input rows -> 117 unique valid ids -> 112 films (5 returned 404).
- Standalones edge out bundles on hit rate in both windows (all years 0.96 vs 0.72; 2000+ 0.73 vs 0.68). Recommendation is metric-sensitive: ROI/profit favor franchises due to blockbuster outliers.
- Shortlist: 3 franchises (The Godfather, The Dark Knight, LOTR:ROTK) + 5 standalones (Shawshank, Schindler's List, Interstellar, Spirited Away, Pulp Fiction).
- Talent read: 19 directors/actors meeting min-count rules.

## Where to look
- `docs/03_client_memo.md` — one-page memo for Kwame (no jargon).
- `docs/01_data_diagnosis.md` — risk-ranked data problems.
- `docs/02_decision_notes.md` — every judgement call, rejected alternative, cost if wrong.
- `docs/04_improvement.md` — the one improvement beyond the brief (automated data-quality report).
- `outputs/tables/` — comparison tables, shortlist, talent read, sensitivity, deal note.
- `outputs/run_log.txt` + `outputs/data_quality_report.txt` — row counts, reconciliation, runtime.