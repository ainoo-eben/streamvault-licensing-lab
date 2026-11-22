# ADR-002: Exclude the 5 missing (404) films with reason; document the 126-vs-127 discrepancy

- **Status:** Accepted
- **Date:** 2026-11-22
- **Decision owner:** Analyst

## Context
Of 117 unique valid ids, 5 returned 404 on details: 8471293, 8471294, 9412887, 9412888, 7733901. The brief states 127 ids but the file has 126 rows. No redirects and no cross-source duplicates (by `imdb_id` or title+year) were found.

## Decision
Exclude the 5 404 ids as "not found on TMDb" with reason recorded in the fetch ledger and `docs/01_data_diagnosis.md`. Do not silently fix the 126-vs-127 row discrepancy; document it and check raw line count vs parsed row count (blank line skipped by CSV readers).

## Alternatives considered

### Alternative A: Retry or substitute missing ids
- **How it would work:** Re-query or replace with a similar title.
- **Why it is attractive:** Keeps the sample at 117.
- **Why rejected:** Substitution invents data; retrying 404s wastes calls (404s are not retried).

### Alternative B: Silently pad to 127
- **How it would work:** Add a row to match the brief.
- **Why it is attractive:** Matches the brief's count.
- **Why rejected:** Hides a source discrepancy; the memo must state what the gap could cost.

## Consequences
- **What this buys:** Every input row has a final status; totals reconcile (126 rows -> 112 films).
- **What this costs:** 5 films of unknown franchise/standalone status are absent.
- **What it costs the client if I am wrong:** Low — the 5 are synthetic-looking sequential ids, likely placeholders; their effect on the recommendation is stated in the memo.
- **What would make me revisit this:** Evidence that any of the 5 is a real, high-value title.

## What this survives
Survives at 500 titles: the ledger records one row per input row (analyzed / 404 / redirected / duplicate / invalid / failed), so missing ids are always accounted for.