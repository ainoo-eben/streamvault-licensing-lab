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

## Summary
112 films fetched from 126 input rows (117 unique valid ids, 5 returned 404). Data is cleaner than expected: no missing money fields, no low-vote ratings, no odd statuses or runtimes. The risks that remain are about franchise completeness, two extreme revenue ratios, and the 5 missing films.

## Reconciliation
| Stage | Rows | Delta | Reason |
|---|---:|---:|---|
| Rows in file | 126 | | brief says 127 (unexplained) |
| Missing / malformed / non-positive | 3 | -3 | Not sent to the API |
| Extra duplicate occurrences | 6 | -6 | Same id repeated |
| Unique valid ids | 117 | | |
| 404 on details | 5 | -5 | Investigated (see above) |
| Films fetched | 112 | | |

## Findings, ranked by risk

### F-01: Partial franchises on the list — Severity: High
- **What it is:** 96/112 films sit in a TMDb collection, but the list may not hold every entry of each collection. A bundle's hit share can be inflated by omitting weak entries.
- **How I detected it:** `in_collection` flag; `belongs_to_collection` shows only a film's own collection, not the full set.
- **Scale:** 96 of 112 films (86%).
- **Effect on the client's number:** Could flip franchise vs standalone comparison if weak entries are missing.
- **What I did about it:** Flagged; Step 10 decides whether to fetch full collections.
- **Residual risk:** Medium — depends on how many entries per collection are absent.

### F-02: 5 missing (404) films — Severity: Medium
- **What it is:** 5 valid ids returned 404 (8471293, 8471294, 9412887, 9412888, 7733901); ids look synthetic/placeholder.
- **How I detected it:** Fetch ledger (`missing_ids`).
- **Scale:** 5 of 117 valid ids (4.3%).
- **Effect on the client's number:** Small unless a missing film is a high-value franchise entry.
- **What I did about it:** Excluded with reason (ADR-002).
- **Residual risk:** Low.

### F-03: Extreme revenue-to-budget ratios — Severity: Medium
- **What it is:** 2 films have revenue/budget ratio > 50x.
- **How I detected it:** Computed ratio on the 112 films.
- **Scale:** 2 of 112.
- **Effect on the client's number:** Can dominate ROI/absolute-profit metrics if used as sensitivity runs.
- **What I did about it:** Flagged for review in Step 7/8; consider capping or reporting separately.
- **Residual risk:** Low if reported.

### F-04: Pre-2000 financial reporting — Severity: Medium
- **What it is:** 41 of 112 films are pre-2000; older budget/revenue figures may be less reliable (no inflation adjustment).
- **How I detected it:** Release-year spread.
- **Scale:** 41 films (37%).
- **Effect on the client's number:** Recommendation may differ between all-years and 2000+ windows (tested in Step 12).
- **What I did about it:** Both windows reported; no inflation adjustment without a defensible index.
- **Residual risk:** Medium — Yaw in Finance will raise this.

### F-05: 126 vs 127 row discrepancy — Severity: Low
- **What it is:** Brief states 127 ids; file has 126 rows.
- **How I detected it:** Row count vs brief.
- **Scale:** 1 row.
- **Effect on the client's number:** Negligible.
- **What I did about it:** Documented, not fixed (ADR-002).
- **Residual risk:** Low.

## Looked wrong, is not wrong
| Apparent problem | Why it looks wrong | Why it is actually fine |
|---|---|---|
| Zero/missing budget and revenue | Roadmap predicted this as a top risk | All 112 films have non-zero budget and revenue |
| Low-vote ratings | Ratings unreliable at low vote counts | Min vote_count is 4,138; none under 100 |
| Odd statuses / runtimes | Possible shorts or unreleased titles | All 112 are "Released", runtimes 60-240 min |
| Missing release dates | Could break the 2000 cut-off | 0 missing dates |
| Adult titles | Could skew the audience metric | 0 adult titles |

## Could not verify
- Collection completeness: TMDb shows only a film's own collection, not whether all entries are on the list (needs one API call per collection).
- Licensing cost and StreamVault viewing data: not available; every metric is a proxy.
