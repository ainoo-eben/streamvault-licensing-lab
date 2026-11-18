# 01 Data Diagnosis

## Source
TMDB API (`api.themoviedb.org/3`): `/movie/{id}` and `/movie/{id}/credits`.

## Known issues
- 404s for removed titles; recorded in `data/processed/fetch_ledger.csv`.
- Redirects / duplicate ids deduplicated by TMDB id.
- Missing crew/cast fields null-filled.

## Input file
Adjoa swaps `data/input/id_list.csv` each cycle (127 ids today, ~500 next year).
