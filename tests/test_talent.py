"""Tests for the talent signal's sample-size and financial eligibility rules."""

import pandas as pd

from src.talent import talent_signal


def test_talent_uses_overall_rating_prior_and_shared_hit_definition() -> None:
    """Shrink ratings toward the list baseline and share the common hit criteria."""
    films = pd.DataFrame(
        [
            {
                "tmdb_id": 1,
                "vote_average": 10.0,
                "vote_count": 2000,
                "budget": 100,
                "revenue": 200,
            },
            {
                "tmdb_id": 2,
                "vote_average": 10.0,
                "vote_count": 2000,
                "budget": 0,
                "revenue": 500,
            },
            {
                "tmdb_id": 3,
                "vote_average": 0.0,
                "vote_count": 2000,
                "budget": 100,
                "revenue": 50,
            },
        ]
    )
    credits = pd.DataFrame(
        [
            {"tmdb_id": 1, "name": "Director A", "role": "crew", "job": "Director"},
            {"tmdb_id": 2, "name": "Director A", "role": "crew", "job": "Director"},
            {"tmdb_id": 1, "name": "Actor A", "role": "cast", "job": None, "cast_order": 0},
            {"tmdb_id": 2, "name": "Actor A", "role": "cast", "job": None, "cast_order": 0},
        ]
    )

    result = talent_signal(
        credits,
        films,
        min_films_director=2,
        min_films_actor=2,
        shrinkage_prior_films=3,
        min_votes=1000,
        min_rating=7.0,
    )

    assert set(result["name"]) == {"Director A", "Actor A"}
    assert result["shrunk_rating"].tolist() == [8.0, 8.0]
    assert result["hit_share"].tolist() == [1.0, 1.0]
    assert result["hit_eligible_films"].tolist() == [1, 1]
    assert result["hit_excluded_films"].tolist() == [1, 1]


def test_talent_signal_returns_empty_table_when_no_one_meets_minimums() -> None:
    """Return a schema-preserving empty result when sample-size rules exclude all."""
    films = pd.DataFrame(
        {
            "tmdb_id": [1],
            "vote_average": [7.0],
            "vote_count": [2000],
            "budget": [100],
            "revenue": [200],
        }
    )
    credits = pd.DataFrame(
        columns=["tmdb_id", "name", "role", "job", "cast_order"]
    )

    result = talent_signal(credits, films)

    assert result.empty
    assert "shrunk_rating" in result.columns
