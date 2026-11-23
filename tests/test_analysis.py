"""Behavior tests for the comparisons, shortlists, and deal-note analysis."""

import pandas as pd
import pytest

from src.analysis import (
    bundle_summary,
    compare_windows,
    deal_note,
    sensitivity,
    shortlist,
)


def _film(
    tmdb_id: int, title: str, year: int, collection: str | None, is_hit: bool
) -> dict:
    """Create a compact film row with configurable collection and hit outcome."""
    return {
        "tmdb_id": tmdb_id,
        "title": title,
        "release_year": year,
        "collection_name": collection,
        "in_collection": collection is not None,
        "vote_count": 2000,
        "vote_average": 7.0,
        "revenue": 200 if is_hit else 50,
        "budget": 100,
    }


def test_compare_windows_uses_film_weighted_rates_and_clear_counts() -> None:
    """Confirm each title, not each bundle, has equal weight in comparisons."""
    frame = pd.DataFrame(
        [
            _film(1, "A: older", 1999, "Series A", True),
            _film(2, "A: weak 1", 2001, "Series A", False),
            _film(3, "A: weak 2", 2001, "Series A", False),
            _film(4, "A: weak 3", 2001, "Series A", False),
            _film(5, "B: hit 1", 2001, "Series B", True),
            _film(6, "B: hit 2", 2001, "Series B", True),
            _film(7, "Standalone hit", 2001, None, True),
            _film(8, "Standalone miss", 2001, None, False),
        ]
    )
    cfg = {
        "hit": {"min_votes": 1000, "min_rating": 7.0},
        "windows": {"all_years": [1900, 2099], "since_2000": [2000, 2099]},
        "franchise": {"min_entries_on_list": 2},
    }

    result = compare_windows(frame, cfg).set_index("window")

    assert result.loc["all_years", "franchise_hit_rate"] == pytest.approx(0.5)
    assert result.loc["all_years", "standalone_hit_rate"] == pytest.approx(0.5)
    assert result.loc["all_years", "n_franchise_bundles"] == 2
    assert result.loc["all_years", "n_franchise_films"] == 6
    assert result.loc["all_years", "n_standalone_films"] == 2
    assert result.loc["since_2000", "franchise_hit_rate"] == pytest.approx(0.4)
    assert result.loc["since_2000", "standalone_hit_rate"] == pytest.approx(0.5)
    assert result.loc["since_2000", "n_franchise_films"] == 5


def test_bundle_summary_identifies_lowest_adjusted_rating_entry() -> None:
    """The weakest bundle entry is based on adjusted, not raw, rating."""
    frame = pd.DataFrame(
        [
            {
                "bundle": "Series A",
                "tmdb_id": 1,
                "title": "Well-supported entry",
                "vote_average": 6.5,
                "vote_count": 10000,
                "revenue": 200,
                "budget": 100,
            },
            {
                "bundle": "Series A",
                "tmdb_id": 2,
                "title": "Few-vote entry",
                "vote_average": 7.0,
                "vote_count": 1,
                "revenue": 200,
                "budget": 100,
            },
        ]
    )

    result = bundle_summary(frame, min_votes=1000, min_rating=7.0).iloc[0]

    assert result["weakest_entry"] == "Few-vote entry"
    assert result["weakest_adjusted_rating"] < 6.1


def test_bundle_summary_excludes_unknown_financials_from_hit_rate() -> None:
    """Unknown financials remain listed but do not enter the hit-rate denominator."""
    frame = pd.DataFrame(
        [
            {
                "bundle": "Series A",
                "tmdb_id": 1,
                "title": "Known hit",
                "vote_average": 8.0,
                "vote_count": 2000,
                "revenue": 200,
                "budget": 100,
            },
            {
                "bundle": "Series A",
                "tmdb_id": 2,
                "title": "Unknown cost",
                "vote_average": 8.0,
                "vote_count": 2000,
                "revenue": 200,
                "budget": 0,
            },
        ]
    )

    result = bundle_summary(frame, min_votes=1000, min_rating=7.0).iloc[0]

    assert result["films"] == 2
    assert result["eligible_films"] == 1
    assert result["excluded_financial_films"] == 1
    assert result["hits"] == 1
    assert result["hit_rate"] == pytest.approx(1.0)


def test_shortlist_ranks_franchise_packages_and_explains_each_target() -> None:
    """Franchise shortlist rows represent packages and disclose listed members."""
    frame = pd.DataFrame(
        [
            _film(1, "A: One", 2020, "Series A", True),
            _film(2, "A: Two", 2021, "Series A", False),
            _film(3, "B: One", 2020, "Series B", True),
            _film(4, "B: Two", 2021, "Series B", True),
            _film(5, "Solo", 2022, None, True),
        ]
    )
    cfg = {
        "hit": {"min_votes": 1000, "min_rating": 7.0},
        "franchise": {"min_entries_on_list": 2},
        "adjusted_rating": {"m": 1000, "c": 6.0},
    }

    result = shortlist(frame, cfg, n_franchise=2, n_standalone=1)

    franchise = result[result["group"] == "franchise"]
    standalone = result[result["group"] == "standalone"]
    assert franchise["target"].tolist() == ["Series B", "Series A"]
    assert franchise["films"].tolist() == [2, 2]
    assert franchise["listed_titles"].tolist() == [
        "B: One; B: Two",
        "A: One; A: Two",
    ]
    assert franchise["weakest_entry"].notna().all()
    assert franchise["reason"].str.contains("Weakest listed entry").all()
    assert standalone["target"].tolist() == ["Solo"]


def test_deal_note_does_not_invent_a_price_ceiling() -> None:
    """The observed hit rate supports priority, not an unsupported bid ceiling."""
    frame = pd.DataFrame(
        [
            _film(1, "A: One", 2020, "Series A", True),
            _film(2, "A: Two", 2021, "Series A", True),
            _film(3, "Solo", 2022, None, True),
        ]
    )
    cfg = {
        "hit": {"min_votes": 1000, "min_rating": 7.0},
        "franchise": {"min_entries_on_list": 2},
        "adjusted_rating": {"m": 1000, "c": 6.0},
    }

    note = deal_note(frame, cfg)

    assert "2 of 2" in note
    assert "cannot set a defensible maximum bid" in note
    assert "modest premium over the median standalone" not in note


def test_sensitivity_handles_groups_without_eligible_financials() -> None:
    """Comparisons are unavailable when either group has no eligible films."""
    frame = pd.DataFrame(
        [
            {
                **_film(1, "Solo", 2020, None, False),
                "budget": 0,
            }
        ]
    )
    cfg = {
        "hit": {"min_votes": 1000, "min_rating": 7.0},
        "franchise": {"min_entries_on_list": 2},
    }

    result = sensitivity(frame, cfg)

    assert result["franchise_score"].isna().all()
    assert result["standalone_score"].isna().all()
    assert not result["comparison_available"].any()
    assert result["standalone_wins"].isna().all()
