# 04 Improvement

## Improvement beyond the brief: automated data-quality report

## The problem it solves
Adjoa re-runs this quarterly on her own with ~500 titles. Each refresh can introduce new problems (new zero-money films, new duplicates, new 404s, input row-count mismatches, shifts in the recommendation) that she would otherwise have to rediscover by hand.

## What I built
`src/report.py` now writes `outputs/data_quality_report.txt` from the current input, fetch ledger, processed tables, and configured hit definition. It reports actual row counts, fetch-status totals, financial exclusions, missing dates, duplicate IDs, raw-file counts, and film-weighted hit rates for both windows. `run_all.py` writes the measured end-to-end runtime and current row totals to `outputs/run_log.txt`; neither report assumes this cycle's 126 inputs or 112 films.

The tests use temporary inputs and tables, so they run from a clean clone without committing fetched data or generated outputs. A tracked five-title sample list lets a new clone run the pipeline after Adjoa supplies a TMDB key; the client-specific `id_list.csv` remains ignored by Git.

## What it is worth to Adjoa
Catches regressions automatically so she does not rediscover them by hand; protects Kwame from a recommendation that silently flips between refreshes.

## What it cost
~30 lines in `src/report.py`; runs in milliseconds as part of `run_all.py`.