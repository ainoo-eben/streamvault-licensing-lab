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
src/report.py + run_all.py -> outputs/data_quality_report.txt + outputs/run_log.txt
```

- `config.yaml` holds the tunable numbers (windows, hit thresholds, minimum film counts, talent shrinkage prior, rate limit, retries). Change a decision there, not in code.
- `notebooks/00_first_look.ipynb` is exploratory only; nothing in the pipeline depends on it.
- `docs/adr/` holds Architecture Decision Records (field selection, missing-film handling).
- Tests use temporary fixtures; they do not depend on ignored local caches or generated reports.

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
3. If you have the quarterly candidate list, copy it to `data/input/id_list.csv` (one `tmdb_id` per row). That client-specific file is intentionally ignored by Git. On a fresh clone without it, the pipeline uses the tracked five-title `data/input/id_sample.csv`. The sample keeps the workflow runnable without editing code; use the actual candidate list for any client recommendation.
4. Run the whole pipeline:
   ```bash
   python run_all.py              # or: make all
   ```
   This runs fetch -> tidy -> checks -> analysis -> talent -> report and writes `data/processed/` and `outputs/`. The diagnostics and run log use counts and elapsed time from that run. Stale cache files from prior lists are ignored during flattening. The client memo in `docs/` is a reviewed deliverable and is not rewritten automatically.

5. Verify:
   ```bash
   .venv\Scripts\python.exe -m pytest tests/ -q
   ```
   Tests run offline and do not require TMDB credentials or prior pipeline outputs.

## Key results (this cycle)
- 126 input rows -> 117 unique valid ids -> 112 films (5 returned 404).
- Standalones edge out franchise films on the film-weighted hit rate in both windows (all years 96.0% vs 72.4%; 2000+ 73.3% vs 71.4%). These rates exclude titles with missing or non-positive budget/revenue. The bundle table reports each franchise's hit rate and weakest listed entry. Recommendation is metric-sensitive: ROI/profit favor franchises due to blockbuster outliers.
- Shortlist: 3 franchise packages (The Lord of the Rings, The Godfather, The Dark Knight) + 5 standalones (Shawshank, Schindler's List, Interstellar, Spirited Away, Pulp Fiction). Package selection is based only on titles in the candidate list; collection completeness is unverified.
- Talent read: 19 directors/actors meeting min-count rules.

## Where to look
- `docs/03_client_memo.md` — one-page memo for Kwame (no jargon).
- `docs/01_data_diagnosis.md` — risk-ranked data problems.
- `docs/02_decision_notes.md` — every judgement call, rejected alternative, cost if wrong.
- `docs/04_improvement.md` — the one improvement beyond the brief (automated data-quality report).
- `outputs/tables/` — comparison tables, shortlist, talent read, sensitivity, deal note.
- `outputs/run_log.txt` + `outputs/data_quality_report.txt` — row counts, reconciliation, runtime.