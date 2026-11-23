"""Reconciliation and join-integrity assertions."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

PROCESSED_DIR = Path("data/processed")


def assert_no_duplicate_films(frame: pd.DataFrame) -> None:
    """Fail if the film table contains the same TMDB id more than once."""
    duplicates = int(frame.duplicated(subset=["tmdb_id"]).sum())
    if duplicates:
        raise AssertionError(f"{duplicates} duplicate films found")


def assert_films_unique(frame: pd.DataFrame) -> None:
    """Assert that every film row has a distinct TMDB id."""
    if frame["tmdb_id"].nunique() != len(frame):
        raise AssertionError("tmdb_id is not unique in films table")


def assert_credits_join(films: pd.DataFrame, credits: pd.DataFrame) -> None:
    """Require credits to reference known films and every film to have credits."""
    film_ids = set(films["tmdb_id"])
    credit_ids = set(credits["tmdb_id"])
    orphan_credits = credit_ids - film_ids
    if orphan_credits:
        raise AssertionError(f"credits reference unknown films: {orphan_credits}")
    missing_credits = film_ids - credit_ids
    if missing_credits:
        raise AssertionError(f"films with no credits: {missing_credits}")


def assert_row_counts(films: pd.DataFrame, expected: int) -> None:
    """Check a film-table row count when an expected count is available."""
    if len(films) != expected:
        raise AssertionError(f"expected {expected} films, got {len(films)}")


def main() -> None:
    """Load processed tables and run the pipeline's join-integrity checks."""
    films = pd.read_parquet(PROCESSED_DIR / "films.parquet")
    credits = pd.read_parquet(PROCESSED_DIR / "credits.parquet")
    assert_no_duplicate_films(films)
    assert_films_unique(films)
    assert_credits_join(films, credits)
    print(f"checks passed: {len(films)} films, {len(credits)} credits, join intact")


if __name__ == "__main__":
    main()
