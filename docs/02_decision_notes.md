# 02 Decision Notes

## Windows
- All years: every release year in the input.
- Since 2000: releases from 2000 onward only.

## Thresholds
- Hit: vote_count >= min_votes and vote_average >= min_rating (see config.yaml).
- Talent: director min 3 films, actor min 5 films.

## Adjusted rating
Bayesian-ish shrinkage toward the mean so low-vote titles do not dominate.
