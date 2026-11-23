"""Tests for nested-response flattening, input accounting, and table integrity."""

import json

import pandas as pd
import pytest

from src.checks import assert_credits_join, assert_films_unique
from src.fetch import read_input_rows, resolve_input_path
from src.tidy import build_analysis_table, build_credits, build_films


def test_tidy_builds_one_film_row_and_joinable_credits(tmp_path) -> None:
    """Flatten nested details and credits while excluding stale cache files."""
    details_dir = tmp_path / "details"
    credits_dir = tmp_path / "credits"
    details_dir.mkdir()
    credits_dir.mkdir()
    (details_dir / "1.json").write_text(
        json.dumps(
            {
                "id": 1,
                "title": "Sample Film",
                "release_date": "2020-01-01",
                "budget": 100,
                "revenue": 200,
                "vote_average": 7.5,
                "vote_count": 2000,
                "belongs_to_collection": {"id": 10, "name": "Sample Series"},
                "genres": [{"name": "Drama"}],
            }
        ),
        encoding="utf-8",
    )
    (credits_dir / "1.json").write_text(
        json.dumps(
            {
                "id": 1,
                "cast": [
                    {"id": 20, "name": "Lead Actor", "character": "Lead", "order": 0}
                ],
                "crew": [{"id": 30, "name": "Director", "job": "Director"}],
            }
        ),
        encoding="utf-8",
    )
    (details_dir / "2.json").write_text(
        json.dumps({"id": 2, "title": "Stale Film"}),
        encoding="utf-8",
    )
    (credits_dir / "2.json").write_text(
        json.dumps({"id": 2, "cast": [], "crew": []}),
        encoding="utf-8",
    )

    films = build_films(details_dir, requested_ids={1})
    credits = build_credits(credits_dir, requested_ids={1})
    analysis = build_analysis_table(films, credits)

    assert len(films) == 1
    assert films.iloc[0]["collection_name"] == "Sample Series"
    assert len(credits) == 2
    assert analysis.iloc[0]["director_count"] == 1
    assert analysis.iloc[0]["cast_count"] == 1
    assert_films_unique(films)
    assert_credits_join(films, credits)


def test_integrity_checks_reject_duplicate_films_and_orphan_credits() -> None:
    """Reject duplicate film rows and credits that cannot join to a film."""
    duplicate_films = pd.DataFrame({"tmdb_id": [1, 1]})
    films = pd.DataFrame({"tmdb_id": [1]})
    orphan_credits = pd.DataFrame({"tmdb_id": [2]})

    with pytest.raises(AssertionError, match="not unique"):
        assert_films_unique(duplicate_films)
    with pytest.raises(AssertionError, match="unknown films"):
        assert_credits_join(films, orphan_credits)


def test_input_parser_tracks_invalid_rows_and_sample_fallback(tmp_path, monkeypatch) -> None:
    """Keep malformed rows visible and use the sample only for the default path."""
    input_path = tmp_path / "ids.csv"
    input_path.write_text("tmdb_id\n155\nbad\n0\n155\n", encoding="utf-8")
    assert read_input_rows(input_path) == [
        (155, "155"),
        (None, "bad"),
        (None, "0"),
        (155, "155"),
    ]

    missing_input = tmp_path / "id_list.csv"
    sample_input = tmp_path / "id_sample.csv"
    sample_input.write_text("tmdb_id\n550\n", encoding="utf-8")
    monkeypatch.setattr("src.fetch.INPUT_CSV", missing_input)
    monkeypatch.setattr("src.fetch.SAMPLE_INPUT_CSV", sample_input)
    assert resolve_input_path({"data": {"input_csv": str(missing_input)}}) == sample_input
