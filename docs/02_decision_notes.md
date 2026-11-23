# 02 Decision Notes

## Windows
- All years: every release year in the input.
- Since 2000: releases from 2000 onward only.

## Field selection
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

## Success metric
- **Headline:** Hit rate. A film is a hit if it clears a commercial bar (revenue > budget, i.e. profitable) AND an audience bar (vote_average >= min_rating with vote_count >= min_votes). Compare hit share in bundles (franchise collections) vs standalones. Speaks directly to the "weak middle entries" argument.
- **Audience signal:** Adjusted rating = Bayesian average pulling low-vote films toward the mean: (v/(v+m))*R + (m/(v+m))*C, with m = min_votes, C = overall mean vote_average.
- **Sensitivity runs:** ROI (revenue/budget), absolute profit (revenue - budget), and a standardized composite. Report whether the recommendation holds under each.
- Stated plainly in the memo: no licensing cost and no StreamVault viewing data exist, so every metric is a proxy.

## Judgement calls
- Zero/missing money: treated as unknown, never as zero; excluded from commercial metrics; count reported. (N/A here — no zeros in this data, but rule stands for reruns.)
- Franchise definition: a film is a franchise member if `belongs_to_collection` is not null. Full collection completeness not verified (one API call per collection needed) — treated as a sensitivity, not a blocker.
- Partial bundle: a collection counts as a franchise bundle only if >= 2 of its entries are on our list; singletons treated as standalone.
- Pre-2000: report both windows (all years and 2000+); no inflation adjustment without a defensible index.
- Hit thresholds, min vote count, mean vs median: see config.yaml.
- Minimum films per director/actor before reporting a signal: see config.yaml.
- The 5 missing films: excluded with reason (ADR-002).
- Duplicates: none found; merge rule not needed this cycle.
- Shortlist ranking: by hit rate, then adjusted rating; flag candidates whose rank depends on a single missing/zero field.

## Thresholds
- Hit: vote_count >= min_votes and vote_average >= min_rating (see config.yaml).
- Talent: director min 3 films, actor min 5 films.

## Adjusted rating
Bayesian-ish shrinkage toward the mean so low-vote titles do not dominate.