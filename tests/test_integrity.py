"""Row counts, no dropped or duplicated films, ledger totals reconcile."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

PROCESSED = Path("data/processed")
RAW_DETAILS = Path("data/raw/details")


def test_films_row_count() -> None:
    films = pd.read_parquet(PROCESSED / "films.parquet")
    assert len(films) == 112


def test_no_duplicate_films() -> None:
    films = pd.read_parquet(PROCESSED / "films.parquet")
    assert films.duplicated(subset=["tmdb_id"]).sum() == 0
    assert films["tmdb_id"].nunique() == len(films)


def test_credits_join_intact() -> None:
    films = pd.read_parquet(PROCESSED / "films.parquet")
    credits = pd.read_parquet(PROCESSED / "credits.parquet")
    assert set(credits["tmdb_id"]).issubset(set(films["tmdb_id"]))
    assert set(films["tmdb_id"]).issubset(set(credits["tmdb_id"]))


def test_analysis_table_matches_films() -> None:
    films = pd.read_parquet(PROCESSED / "films.parquet")
    analysis = pd.read_parquet(PROCESSED / "analysis_table.parquet")
    assert len(analysis) == len(films)
    assert analysis["tmdb_id"].nunique() == len(films)


def test_raw_files_not_overwritten() -> None:
    files = list(RAW_DETAILS.glob("*.json"))
    assert len(files) == 112
    for f in files:
        with f.open() as fh:
            data = json.load(fh)
        assert data.get("id") == int(f.stem)


def test_ledger_totals_reconcile() -> None:
    ledger = pd.read_csv("data/processed/fetch_ledger.csv")
    assert len(ledger) == 126
    counts = ledger["status"].value_counts().to_dict()
    assert counts.get("ok", 0) == 112
    assert counts.get("404", 0) == 5
    assert counts.get("invalid", 0) == 3
    assert counts.get("duplicate", 0) == 6