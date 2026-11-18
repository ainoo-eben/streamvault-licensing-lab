"""Success metrics: hit rate and adjusted rating."""

from __future__ import annotations

import pandas as pd


def hit_rate(frame: pd.DataFrame, min_votes: int = 1000) -> float:
    eligible = frame[frame["vote_count"] >= min_votes]
    if eligible.empty:
        return 0.0
    return float((eligible["vote_average"] >= 7.0).mean())


def adjusted_rating(vote_average: float, vote_count: int, m: int = 1000, c: float = 6.0) -> float:
    return (vote_count / (vote_count + m)) * vote_average + (m / (vote_count + m)) * c
