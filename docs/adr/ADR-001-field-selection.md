# ADR-001: Field selection for the licensing analysis

- **Status:** Accepted
- **Date:** 2026-11-22
- **Decision owner:** Analyst

## Context
TMDB returns ~40 fields per movie. We need only those that help answer "what is worth licensing?" and must keep the table small and defensible. TMDb's `popularity` is a daily snapshot, not a stable property of the film.

## Decision
Keep: `title`, `release_date`, `budget`, `revenue`, `vote_average`, `vote_count`, `belongs_to_collection`, `runtime`, `status`, `original_language`, `adult`, and credits (directors, lead actors). Exclude `popularity`.

## Alternatives considered

### Alternative A: Keep all TMDB fields
- **How it would work:** Ingest everything and filter later.
- **Why it is attractive:** Nothing lost up front.
- **Why rejected:** Bloats the table, invites over-cleaning, and `popularity` would be misread as a stable signal.

### Alternative B: Drop `budget`/`revenue` entirely
- **How it would work:** Rely only on audience metrics.
- **Why it is attractive:** Avoids the zero/missing money problem.
- **Why rejected:** Commercial return is central to the licensing question; exclusion would be stated as a limitation, not a fix.

## Consequences
- **What this buys:** A small, explainable feature set traceable to the business question.
- **What this costs:** Any later analysis wanting a dropped field needs a re-fetch.
- **What it costs the client if I am wrong:** Low — fields can be added without re-running the whole pipeline.
- **What would make me revisit this:** A shortlist candidate whose rank depends on a field we dropped.

## What this survives
Survives at 500 titles: field list is fixed in `src/tidy.py` and `config.yaml`; adding a field is a one-line change.