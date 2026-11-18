# StreamVault – Initial Data Diagnosis

## 1. Input Overview

**Source:** `id_list.csv`

| Attribute | Finding |
|---|---:|
| Total rows | 126 |
| Columns | 1 (`tmdb_id`) |
| Missing IDs | 1 |
| Duplicate occurrences | 6 |
| Unique non-missing IDs | 119 |

## 2. Data Quality Findings

| ID | What I observed | Verdict | Decision |
|---|---|---|---|
| F01 | One missing ID at row index 108. | Missing value | Preserve and record the row; do not send it to the API. |
| F02 | Six IDs are duplicated: `155`, `1891`, `278`, `550`, `603`, `680`. | Duplicate records | Keep one occurrence of each ID for acquisition and record the duplicates. |
| F03 | ID `-1` was found. | Invalid identifier | Exclude from API requests and record as an exception. |
| F04 | ID `tt0468569` was found. | Wrong identifier format | Do not convert or send to TMDb as a movie ID; record for investigation. |

## 3. Cleaning Summary

| Category | Count |
|---|---:|
| Original rows | 126 |
| Missing IDs | 1 |
| Malformed IDs | 1 |
| Non-positive IDs | 1 |
| Extra duplicate occurrences | 6 |
| Unique valid IDs | 117 |

**Reconciliation:**

`126 = 1 + 1 + 1 + 6 + 117`

I now have **117 unique positive numeric IDs** eligible for TMDb API acquisition.

## 4. Outstanding Issue

The project brief specifies 127 candidate IDs, but the supplied file contains 126 rows.

The reason for this difference has not yet been established. It will be investigated rather than assuming an ID is missing.

## 5. Engineering Decisions

- Preserve the original input instead of overwriting it.
- Validate identifiers before converting data types.
- Record missing, malformed and non-positive values separately.
- Remove duplicate occurrences only from the acquisition list, not from the original evidence.
- Account for every input row so that no records disappear silently.

**Current stage:** Initial input diagnosis and cleaning completed. TMDb API acquisition has not started.
