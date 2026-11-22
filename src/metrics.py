"""Success metrics: hit rate and adjusted rating."""

from __future__ import annotations

import pandas as pd


def is_hit(frame: pd.DataFrame, min_votes: int = 1000, min_rating: float = 7.0) -> pd.Series:
    commercial = frame["revenue"] > frame["budget"]
    audience = (frame["vote_count"] >= min_votes) & (frame["vote_average"] >= min_rating)
    return commercial & audience


def hit_rate(frame: pd.DataFrame, min_votes: int = 1000, min_rating: float = 7.0) -> float:
    if frame.empty:
        return 0.0
    return float(is_hit(frame, min_votes, min_rating).mean())


def adjusted_rating(vote_average: float, vote_count: int, m: int = 1000, c: float = 6.0) -> float:
    return (vote_count / (vote_count + m)) * vote_average + (m / (vote_count + m)) * c


def add_adjusted_rating(frame: pd.DataFrame, m: int = 1000, c: float = 6.0) -> pd.DataFrame:
    out = frame.copy()
    out["adjusted_rating"] = out.apply(
        lambda r: adjusted_rating(r["vote_average"], r["vote_count"], m, c), axis=1
    )
    return out


def roi(frame: pd.DataFrame) -> pd.Series:
    return frame["revenue"] / frame["budget"].replace(0, pd.NA)


def profit(frame: pd.DataFrame) -> pd.Series:
    return frame["revenue"] - frame["budget"]