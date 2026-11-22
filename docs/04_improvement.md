# 04 Improvement

## Improvement beyond the brief: automated data-quality report

## The problem it solves
Adjoa re-runs this quarterly on her own with ~500 titles. Each refresh can introduce new problems (new zero-money films, new duplicates, new 404s, input row-count mismatches, shifts in the recommendation) that she would otherwise have to rediscover by hand.

## What I built
`src/report.py` now runs a data-quality report on every pipeline run, writing `outputs/data_quality_report.txt`. It flags: input row count vs 126, zero/missing money films, duplicate film ids, missing release dates, raw-file-vs-film count mismatch, and whether the franchise/standalone hit-rate recommendation has shifted.

## What it is worth to Adjoa
Catches regressions automatically so she does not rediscover them by hand; protects Kwame from a recommendation that silently flips between refreshes.

## What it cost
~30 lines in `src/report.py`; runs in milliseconds as part of `run_all.py`.