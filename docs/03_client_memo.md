# 03 Client Memo

## Bottom line
Pipeline ingests TMDB ids, fetches details + credits, validates the join, and
produces a shortlist of licensing candidates split by franchise vs standalone.

## What we deliver
- Clean joined table: `data/processed/analysis_table.parquet`
- Shortlist CSV: `outputs/tables/`
- Talent read (director/actor signal): `outputs/tables/`
- Run log: `outputs/run_log.txt`

## Next steps
Review `02_decision_notes.md` before changing thresholds in `config.yaml`.
