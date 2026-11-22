# 02 Decision Notes

## Field selection (Step 3)
Kept (helps answer "what is worth licensing?"):

| Field | Why it matters | Caveat |
|---|---|---|
| title, release_date | Identity, and the 2000 cut-off | Check for missing or future dates |
| budget, revenue | Commercial return | 0 usually means unknown, not zero |
| vote_average, vote_count | Audience quality and how trustworthy it is | Low vote counts make ratings unreliable |
| belongs_to_collection | Franchise membership | Shows only a film's collection, not whether the list holds all of it |
| runtime, status, original_language, adult | Checks for odd records (shorts, unreleased, non-English) | Odd is not the same as wrong. Do not over-clean. |
| Credits: directors, lead actors | Talent signal | Small samples per person |

Left out on purpose: TMDb's `popularity` field (daily snapshot, not a stable property of the film).
- Since 2000: releases from 2000 onward only.

## Thresholds
- Hit: vote_count >= min_votes and vote_average >= min_rating (see config.yaml).
- Talent: director min 3 films, actor min 5 films.

## Adjusted rating
Bayesian-ish shrinkage toward the mean so low-vote titles do not dominate.
