"""Franchise vs standalone analysis across both windows, plus sensitivity runs."""

from __future__ import annotations

import yaml
from pathlib import Path

import pandas as pd

try:
    from src.metrics import (
        add_adjusted_rating,
        financial_data_available,
        is_hit,
        profit,
        roi,
    )
except ModuleNotFoundError:
    from metrics import add_adjusted_rating, financial_data_available, is_hit, profit, roi

CONFIG_PATH = Path("config.yaml")
PROCESSED_DIR = Path("data/processed")
OUTPUT_DIR = Path("outputs/tables")


def load_config(path: Path = CONFIG_PATH) -> dict:
    """Load analysis thresholds, windows, and rating configuration."""
    with path.open() as f:
        return yaml.safe_load(f)


def classify(frame: pd.DataFrame, min_entries: int = 2) -> pd.DataFrame:
    """Classify listed collections with enough candidate films as franchises.

    A film in a TMDB collection is treated as standalone if too few of that
    collection's entries appear in this candidate list.
    """
    counts = frame.groupby("collection_name").size() if "collection_name" in frame else pd.Series(dtype=int)
    valid_collections = set(counts[counts >= min_entries].index) if len(counts) else set()
    out = frame.copy()
    out["is_franchise"] = out["in_collection"] & out["collection_name"].isin(valid_collections)
    out["bundle"] = out["collection_name"].where(out["is_franchise"], "standalone")
    return out


def window(frame: pd.DataFrame, start_year: int) -> pd.DataFrame:
    """Return a copy containing films released in or after ``start_year``."""
    return frame[frame["release_year"] >= start_year].copy()


def bundle_summary(
    frame: pd.DataFrame,
    min_votes: int,
    min_rating: float,
    m: int = 1000,
    c: float = 6.0,
) -> pd.DataFrame:
    """Summarize listed titles per bundle, including eligible hit rates and weakest rating."""
    frame = frame.copy()
    frame["financially_eligible"] = financial_data_available(frame)
    frame["hit"] = is_hit(frame, min_votes, min_rating)
    frame = add_adjusted_rating(frame, m, c)
    frame["hit_for_rate"] = frame["hit"].astype("Float64").where(
        frame["financially_eligible"]
    )
    # Null out ineligible hit flags so they do not dilute the bundle hit rate.
    weakest_entries = (
        frame.sort_values(["bundle", "adjusted_rating", "title"])
        .drop_duplicates("bundle")[["bundle", "title", "adjusted_rating"]]
        .rename(
            columns={
                "title": "weakest_entry",
                "adjusted_rating": "weakest_adjusted_rating",
            }
        )
    )
    grouped = frame.groupby("bundle").agg(
        films=("tmdb_id", "count"),
        listed_titles=(
            "title",
            lambda titles: "; ".join(sorted(titles.dropna().astype(str))),
        ),
        eligible_films=("financially_eligible", "sum"),
        excluded_financial_films=("financially_eligible", lambda values: (~values).sum()),
        hits=("hit_for_rate", "sum"),
        hit_rate=("hit_for_rate", "mean"),
        mean_adjusted_rating=("adjusted_rating", "mean"),
        median_rating=("vote_average", "median"),
        mean_rating=("vote_average", "mean"),
        min_rating=("vote_average", "min"),
        median_revenue=("revenue", "median"),
    ).reset_index()
    grouped = grouped.merge(weakest_entries, on="bundle", validate="one_to_one")
    grouped[["eligible_films", "excluded_financial_films", "hits"]] = grouped[
        ["eligible_films", "excluded_financial_films", "hits"]
    ].astype(int)
    grouped["is_franchise"] = grouped["bundle"] != "standalone"
    return grouped.sort_values("hit_rate", ascending=False)


def compare_windows(frame: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Compare franchise and standalone film-level hit rates in both year windows."""
    min_votes = cfg["hit"]["min_votes"]
    min_rating = cfg["hit"]["min_rating"]
    rows = []
    for label, start in [("all_years", cfg["windows"]["all_years"][0]),
                         ("since_2000", cfg["windows"]["since_2000"][0])]:
        sub = window(frame, start)
        sub = classify(sub, cfg["franchise"]["min_entries_on_list"])
        sub["financially_eligible"] = financial_data_available(sub)
        sub["hit"] = is_hit(sub, min_votes, min_rating)
        franchise_films = sub[sub["is_franchise"]]
        standalone_films = sub[~sub["is_franchise"]]
        franchise_eligible = franchise_films[franchise_films["financially_eligible"]]
        standalone_eligible = standalone_films[standalone_films["financially_eligible"]]
        rows.append(
            {
                "window": label,
                "start_year": start,
                "n_films": len(sub),
                "n_franchise_bundles": franchise_films["bundle"].nunique(),
                "n_franchise_films": len(franchise_films),
                "n_standalone_films": len(standalone_films),
                "n_franchise_financially_eligible": len(franchise_eligible),
                "n_standalone_financially_eligible": len(standalone_eligible),
                "n_franchise_financially_excluded": (
                    len(franchise_films) - len(franchise_eligible)
                ),
                "n_standalone_financially_excluded": (
                    len(standalone_films) - len(standalone_eligible)
                ),
                "n_franchise_hits": int(franchise_eligible["hit"].sum()),
                "n_standalone_hits": int(standalone_eligible["hit"].sum()),
                "franchise_hit_rate": (
                    franchise_eligible["hit"].mean()
                    if len(franchise_eligible)
                    else float("nan")
                ),
                "standalone_hit_rate": (
                    standalone_eligible["hit"].mean()
                    if len(standalone_eligible)
                    else float("nan")
                ),
                "franchise_median_rating": (
                    franchise_films["vote_average"].median()
                    if len(franchise_films)
                    else 0.0
                ),
                "standalone_median_rating": (
                    standalone_films["vote_average"].median()
                    if len(standalone_films)
                    else 0.0
                ),
            }
        )
    return pd.DataFrame(rows)


def shortlist(
    frame: pd.DataFrame, cfg: dict, n_franchise: int = 3, n_standalone: int = 5
) -> pd.DataFrame:
    """Rank franchise packages and standalone titles with reasons for selection."""
    min_votes = cfg["hit"]["min_votes"]
    min_rating = cfg["hit"]["min_rating"]
    f = frame.copy()
    f["financially_eligible"] = financial_data_available(f)
    f["hit"] = is_hit(f, min_votes, min_rating)
    f = add_adjusted_rating(f, cfg["adjusted_rating"]["m"], cfg["adjusted_rating"]["c"])
    f = classify(f, cfg["franchise"]["min_entries_on_list"])
    franchise_bundles = bundle_summary(
        f,
        min_votes,
        min_rating,
        cfg["adjusted_rating"]["m"],
        cfg["adjusted_rating"]["c"],
    )
    franchise_bundles = franchise_bundles[franchise_bundles["is_franchise"]]
    franchise_bundles = franchise_bundles.sort_values(
        ["hit_rate", "mean_adjusted_rating", "eligible_films", "bundle"],
        ascending=[False, False, False, True],
        na_position="last",
    ).head(n_franchise)

    standalone_films = f[~f["is_franchise"]].copy()
    # A hit flag dominates the ranking; adjusted rating breaks ties among hits.
    standalone_films["rank_score"] = (
        standalone_films["hit"].astype(int) * 100
        + standalone_films["adjusted_rating"]
    )
    standalone_films = standalone_films.sort_values(
        ["rank_score", "title"], ascending=[False, True]
    ).head(n_standalone)

    rows = []
    for bundle in franchise_bundles.itertuples(index=False):
        if bundle.eligible_films:
            rate = float(bundle.hit_rate)
            reason = (
                f"{bundle.hits}/{bundle.eligible_films} financially eligible listed "
                f"films meet the hit criteria ({rate:.1%}); mean adjusted rating "
                f"{bundle.mean_adjusted_rating:.2f}. Weakest listed entry: "
                f"{bundle.weakest_entry} ({bundle.weakest_adjusted_rating:.2f})."
            )
        else:
            rate = None
            reason = (
                "No listed films have eligible financial data; hit rate unavailable. "
                f"Weakest listed entry by adjusted rating: {bundle.weakest_entry} "
                f"({bundle.weakest_adjusted_rating:.2f})."
            )
        rows.append(
            {
                "group": "franchise",
                "target": bundle.bundle,
                "listed_titles": bundle.listed_titles,
                "tmdb_id": None,
                "title": None,
                "release_year": None,
                "films": bundle.films,
                "eligible_films": bundle.eligible_films,
                "excluded_financial_films": bundle.excluded_financial_films,
                "hits": bundle.hits,
                "hit_rate": rate,
                "adjusted_rating": bundle.mean_adjusted_rating,
                "weakest_entry": bundle.weakest_entry,
                "weakest_adjusted_rating": bundle.weakest_adjusted_rating,
                "reason": reason,
            }
        )

    for film in standalone_films.itertuples(index=False):
        if film.financially_eligible and film.hit:
            reason = (
                f"Profitable with the required vote count and rating; adjusted rating "
                f"{film.adjusted_rating:.2f}."
            )
        elif film.financially_eligible:
            failures = []
            if film.revenue <= film.budget:
                failures.append("revenue does not exceed budget")
            if pd.isna(film.vote_count) or film.vote_count < min_votes:
                failures.append(f"fewer than {min_votes} votes")
            if pd.isna(film.vote_average) or film.vote_average < min_rating:
                failures.append(f"rating below {min_rating}")
            reason = (
                f"Does not qualify: {', '.join(failures)}; adjusted rating "
                f"{film.adjusted_rating:.2f}."
            )
        else:
            reason = (
                f"Financial data unavailable or non-positive; excluded from financial "
                f"hit rates. Adjusted rating {film.adjusted_rating:.2f}."
            )
        rows.append(
            {
                "group": "standalone",
                "target": film.title,
                "listed_titles": film.title,
                "tmdb_id": film.tmdb_id,
                "title": film.title,
                "release_year": film.release_year,
                "films": 1,
                "eligible_films": int(film.financially_eligible),
                "excluded_financial_films": int(not film.financially_eligible),
                "hits": int(film.hit),
                "hit_rate": float(film.hit) if film.financially_eligible else None,
                "adjusted_rating": film.adjusted_rating,
                "weakest_entry": None,
                "weakest_adjusted_rating": None,
                "reason": reason,
            }
        )

    return pd.DataFrame(rows)


def sensitivity(frame: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Recompute group comparisons across alternate thresholds and definitions."""
    min_votes_opts = [500, 1000, 2000]
    min_rating_opts = [6.5, 7.0, 7.5]
    metrics = ["hit_rate", "roi", "profit", "composite"]
    franchise_defs = ["collection_only", "min_entries"]
    rows = []
    for mv in min_votes_opts:
        for mr in min_rating_opts:
            for fdef in franchise_defs:
                for metric in metrics:
                    sub = frame.copy()
                    min_entries = 1 if fdef == "collection_only" else cfg["franchise"]["min_entries_on_list"]
                    sub = classify(sub, min_entries)
                    sub["hit"] = is_hit(sub, mv, mr)
                    financially_eligible = financial_data_available(sub)
                    if metric == "hit_rate":
                        sub["score"] = sub["hit"].astype(float).where(financially_eligible)
                    elif metric == "roi":
                        sub["score"] = roi(sub)
                    elif metric == "profit":
                        sub["score"] = profit(sub)
                    else:
                        sub["score"] = (
                            sub["hit"].astype(float) * 0.5
                            + (sub["vote_average"] / 10) * 0.5
                        ).where(financially_eligible)
                    frac = sub[sub["is_franchise"]]["score"].mean()
                    stand = sub[~sub["is_franchise"]]["score"].mean()
                    franchise_score = (
                        round(float(frac), 4) if pd.notna(frac) else None
                    )
                    standalone_score = (
                        round(float(stand), 4) if pd.notna(stand) else None
                    )
                    comparison_available = pd.notna(frac) and pd.notna(stand)
                    rows.append({
                        "metric": metric,
                        "franchise_def": fdef,
                        "min_votes": mv,
                        "min_rating": mr,
                        "franchise_score": franchise_score,
                        "standalone_score": standalone_score,
                        "comparison_available": comparison_available,
                        "standalone_wins": (
                            bool(stand > frac) if comparison_available else None
                        ),
                    })
    return pd.DataFrame(rows)


def deal_note(frame: pd.DataFrame, cfg: dict) -> str:
    """Describe the leading listed franchise without implying a maximum bid."""
    sl = shortlist(frame, cfg)
    top_franchises = sl[sl["group"] == "franchise"]
    if top_franchises.empty:
        return "Deal note: no franchise bundle met the configured listing rule."
    top_franchise = top_franchises.iloc[0]
    if pd.isna(top_franchise["hit_rate"]):
        hit_measure = "no listed entry has eligible financial data"
    else:
        hit_measure = (
            f"{int(top_franchise['hits'])} of {int(top_franchise['eligible_films'])} "
            f"financially eligible listed entries are hits "
            f"({top_franchise['hit_rate']:.1%})"
        )
    note = (
        f"Deal note - strongest listed franchise package: {top_franchise['target']}. "
        f"The most decision-relevant observed number is {hit_measure}; its weakest "
        f"listed entry is {top_franchise['weakest_entry']} "
        f"({top_franchise['weakest_adjusted_rating']:.2f} adjusted rating). "
        "This is a negotiation priority, not a price recommendation: without a license "
        "price, rights term, expected viewing, and delivery costs, this analysis cannot "
        "set a defensible maximum bid. Do not approve a premium from these proxies alone."
    )
    return note


def main() -> None:
    """Generate the comparison, bundle, shortlist, sensitivity, and deal-note outputs."""
    cfg = load_config()
    frame = pd.read_parquet(PROCESSED_DIR / "analysis_table.parquet")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    windows = compare_windows(frame, cfg)
    windows.to_csv(OUTPUT_DIR / "window_comparison.csv", index=False)
    print(windows.to_string(index=False))

    bundle_summaries = []
    for label, start in [
        ("all_years", cfg["windows"]["all_years"][0]),
        ("since_2000", cfg["windows"]["since_2000"][0]),
    ]:
        sub = classify(window(frame, start), cfg["franchise"]["min_entries_on_list"])
        summary = bundle_summary(
            sub,
            cfg["hit"]["min_votes"],
            cfg["hit"]["min_rating"],
            cfg["adjusted_rating"]["m"],
            cfg["adjusted_rating"]["c"],
        )
        summary.insert(0, "window", label)
        bundle_summaries.append(summary)
    bs = pd.concat(bundle_summaries, ignore_index=True)
    bs.to_csv(OUTPUT_DIR / "bundle_summary.csv", index=False)

    sl = shortlist(frame, cfg)
    sl.to_csv(OUTPUT_DIR / "shortlist.csv", index=False)
    print("\nShortlist:")
    print(sl.to_string(index=False))

    sens = sensitivity(frame, cfg)
    sens.to_csv(OUTPUT_DIR / "sensitivity.csv", index=False)
    flips = sens[
        sens["comparison_available"] & sens["standalone_wins"].eq(False)
    ]
    print(f"\nSensitivity: {len(sens)} variants, {len(flips)} where franchise wins")

    note = deal_note(frame, cfg)
    (OUTPUT_DIR / "deal_note.txt").write_text(note, encoding="utf-8")
    print("\n" + note)
    if len(flips):
        print(flips.to_string(index=False))


if __name__ == "__main__":
    main()
