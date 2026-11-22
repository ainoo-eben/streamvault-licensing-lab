# 01 Data Diagnosis

## Source
TMDB API (`api.themoviedb.org/3`): `/movie/{id}` and `/movie/{id}/credits`.

## Input account (126 rows)
- Brief says 127 ids; file has 126 rows. Documented, not silently fixed (blank-line skip by CSV readers checked).
- 1 missing, 1 malformed, 1 non-positive, 6 extra duplicate occurrences -> 117 unique valid ids.
- 5 of the 117 returned 404 on details -> 112 films fetched.

## Missing films (404 on details)
| tmdb_id | Status |
|---|---|
| 8471293 | 404 |
| 8471294 | 404 |
| 9412887 | 404 |
| 9412888 | 404 |
| 7733901 | 404 |

Ids look synthetic/sequential (8471293/8471294, 9412887/9412888, 7733901) — likely placeholder entries from the merged source list, not real TMDb titles. No redirects detected (no film returned a different `id` than requested). Excluded-with-reason; bias risk low but stated.

## Cross-source duplicates
- By `imdb_id`: none.
- By `(title, release year)`: none.
No duplicate films to merge.

## Raw JSON structure (Step 1)
- **Details (`/movie/{id}`):** one object per film -> one row per film. Top-level scalar fields (title, release_date, budget, revenue, vote_average, vote_count, runtime, status, original_language, adult) plus nested `belongs_to_collection` (dict or None) and `genres` (list).
- **Credits (`/movie/{id}/credits`):** one object with `cast` and `crew` lists -> many rows per film (one per person). Directors are not a field; they are `crew` entries where `job == "Director"` (a film can have more than one).
- Hence details -> `films` table (1 row/film) and credits -> `credits` table (1 row/film-person).
- 404s for removed/placeholder titles; recorded in `data/processed/fetch_ledger.csv`.
- Missing crew/cast fields null-filled.
- Zero/missing budget and revenue treated as unknown, never as zero (decided in Phase 3).
- Partial franchises: collection shows only a film's own collection, not whether all entries are on the list.

## Input file
Adjoa swaps `data/input/id_list.csv` each cycle (127 ids stated, 126 rows this cycle).
