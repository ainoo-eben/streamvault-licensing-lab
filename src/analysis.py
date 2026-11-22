"""Franchise vs standalone analysis across both windows, plus sensitivity runs."""

from __future__ import annotations

import yaml
from pathlib import Path

import pandas as pd

try:
    from src.metrics import is_hit, hit_rate, add_adjusted_rating
except ModuleNotFoundError:
    from metrics import is_hit, hit_rate, add_adjusted_rating

CONFIG_PATH = Path("config.yaml")
PROCESSED_DIR = Path("data/processed")
OUTPUT_DIR = Path("outputs/tables")


def load_config(path: Path = CONFIG_PATH) -> dict:
    with path.open() as f:
        return yaml.safe_load(f)


def classify(frame: pd.DataFrame, min_entries: int = 2) -> pd.DataFrame:
    counts = frame.groupby("collection_name").size() if "collection_name" in frame else pd.Series(dtype=int)
    valid_collections = set(counts[counts >= min_entries].index) if len(counts) else set()
    out = frame.copy()
    out["is_franchise"] = out["in_collection"] & out["collection_name"].isin(valid_collections)
    out["bundle"] = out["collection_name"].where(out["is_franchise"], "standalone")
    return out


def window(frame: pd.DataFrame, start_year: int) -> pd.DataFrame:
    return frame[frame["release_year"] >= start_year].copy()


def bundle_summary(frame: pd.DataFrame, min_votes: int, min_rating: float) -> pd.DataFrame:
    frame = frame.copy()
    frame["hit"] = is_hit(frame, min_votes, min_rating)
    grouped = frame.groupby("bundle").agg(
        films=("tmdb_id", "count"),
        hits=("hit", "sum"),
        hit_rate=("hit", "mean"),
        median_rating=("vote_average", "median"),
        mean_rating=("vote_average", "mean"),
        min_rating=("vote_average", "min"),
        median_revenue=("revenue", "median"),
    ).reset_index()
    grouped["is_franchise"] = grouped["bundle"] != "standalone"
    return grouped.sort_values("hit_rate", ascending=False)


def compare_windows(frame: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    min_votes = cfg["hit"]["min_votes"]
    min_rating = cfg["hit"]["min_rating"]
    rows = []
    for label, start in [("all_years", cfg["windows"]["all_years"][0]),
                         ("since_2000", cfg["windows"]["since_2000"][0])]:
        sub = window(frame, start)
        sub = classify(sub, cfg["franchise"]["min_entries_on_list"])
        bs = bundle_summary(sub, min_votes, min_rating)
        frac = bs[bs["is_franchise"]]
        stand = bs[~bs["is_franchise"]]
        rows.append({
            "window": label,
            "start_year": start,
            "n_films": len(sub),
            "n_franchise_bundles": len(frac),
            "n_standalone": len(stand),
            "franchise_hit_rate": frac["hit_rate"].mean() if len(frac) else 0.0,
            "standalone_hit_rate": stand["hit_rate"].mean() if len(stand) else 0.0,
            "franchise_median_rating": frac["median_rating"].median() if len(frac) else 0.0,
            "standalone_median_rating": stand["median_rating"].median() if len(stand) else 0.0,
        })
    return pd.DataFrame(rows)


def shortlist(frame: pd.DataFrame, cfg: dict, n_franchise: int = 3, n_standalone: int = 5) -> pd.DataFrame:
    min_votes = cfg["hit"]["min_votes"]
    min_rating = cfg["hit"]["min_rating"]
    f = frame.copy()
    f["hit"] = is_hit(f, min_votes, min_rating)
    f = add_adjusted_rating(f, cfg["adjusted_rating"]["m"], cfg["adjusted_rating"]["c"])
    f["rank_score"] = f["hit"].astype(int) * 100 + f["adjusted_rating"]
    f = classify(f, cfg["franchise"]["min_entries_on_list"])
    frac = f[f["is_franchise"]].sort_values("rank_score", ascending=False).head(n_franchise)
    stand = f[~f["is_franchise"]].sort_values("rank_score", ascending=False).head(n_standalone)
    out = pd.concat([frac, stand], ignore_index=True)
    out["group"] = out["is_franchise"].map({True: "franchise", False: "standalone"})
    return out[["group", "tmdb_id", "title", "release_year", "hit", "adjusted_rating", "revenue", "budget"]]


def sensitivity(frame: pd.DataFrame, cfg: dict) -> pd.DataFrame:
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
                    if metric == "hit_rate":
                        sub["score"] = sub["hit"].astype(float)
                    elif metric == "roi":
                        sub["score"] = (sub["revenue"] / sub["budget"].replace(0, pd.NA)).fillna(0)
                    elif metric == "profit":
                        sub["score"] = sub["revenue"] - sub["budget"]
                    else:
                        sub["score"] = sub["hit"].astype(float) * 0.5 + (sub["vote_average"] / 10) * 0.5
                    frac = sub[sub["is_franchise"]]["score"].mean()
                    stand = sub[~sub["is_franchise"]]["score"].mean()
                    rows.append({
                        "metric": metric,
                        "franchise_def": fdef,
                        "min_votes": mv,
                        "min_rating": mr,
                        "franchise_score": round(float(frac), 4),
                        "standalone_score": round(float(stand), 4),
                        "standalone_wins": bool(stand > frac),
                    })
    return pd.DataFrame(rows)


def driving_number(frame: pd.DataFrame, cfg: dict) -> str:
    min_votes = cfg["hit"]["min_votes"]
    min_rating = cfg["hit"]["min_rating"]
    m = cfg["adjusted_rating"]["m"]
    c = cfg["adjusted_rating"]["c"]
    f = classify(frame.copy(), cfg["franchise"]["min_entries_on_list"])
    f = f[f["is_franchise"]].copy()
    f["hit"] = is_hit(f, min_votes, min_rating)

    def rank_score(df: pd.DataFrame) -> pd.Series:
        ar = df.apply(lambda r: (r["vote_count"] / (r["vote_count"] + m)) * r["vote_average"]
                      + (m / (r["vote_count"] + m)) * c, axis=1)
        return df["hit"].astype(int) * 100 + ar

    baseline = rank_score(f)
    base_top = baseline.idxmax()

    impacts: dict[str, int] = {}
    for field in ["budget", "revenue", "vote_average", "vote_count"]:
        perturbed = f.copy()
        perturbed[field] = 0
        perturbed["hit"] = is_hit(perturbed, min_votes, min_rating)
        new_score = rank_score(perturbed)
        new_top = new_score.idxmax()
        impacts[field] = 0 if new_top == base_top else 1
        # magnitude: how far the original top drops
        impacts[field] = int((baseline[base_top] - new_score[base_top]))

    return max(impacts, key=impacts.get)


def deal_note(frame: pd.DataFrame, cfg: dict) -> str:
    sl = shortlist(frame, cfg)
    top_franchise = sl[sl["group"] == "franchise"].iloc[0]
    driver = driving_number(frame, cfg)
    note = (
        f"Deal note - strongest franchise: {top_franchise['title']} "
        f"(tmdb_id {top_franchise['tmdb_id']}, {top_franchise['release_year']}). "
        f"Pay up to a modest premium over the median standalone (adjusted rating "
        f"{top_franchise['adjusted_rating']:.2f}); the single number that most drove "
        f"the ranking is '{driver}' - blanking it moves the top franchise's score "
        f"the most. Treat any bid above the standalone median as needing sign-off."
    )
    return note


def main() -> None:
    cfg = load_config()
    frame = pd.read_parquet(PROCESSED_DIR / "analysis_table.parquet")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    windows = compare_windows(frame, cfg)
    windows.to_csv(OUTPUT_DIR / "window_comparison.csv", index=False)
    print(windows.to_string(index=False))

    f2000 = classify(window(frame, cfg["windows"]["since_2000"][0]), cfg["franchise"]["min_entries_on_list"])
    bs = bundle_summary(f2000, cfg["hit"]["min_votes"], cfg["hit"]["min_rating"])
    bs.to_csv(OUTPUT_DIR / "bundle_summary.csv", index=False)

    sl = shortlist(frame, cfg)
    sl.to_csv(OUTPUT_DIR / "shortlist.csv", index=False)
    print("\nShortlist:")
    print(sl.to_string(index=False))

    sens = sensitivity(frame, cfg)
    sens.to_csv(OUTPUT_DIR / "sensitivity.csv", index=False)
    flips = sens[~sens["standalone_wins"]]
    print(f"\nSensitivity: {len(sens)} variants, {len(flips)} where franchise wins")

    note = deal_note(frame, cfg)
    (OUTPUT_DIR / "deal_note.txt").write_text(note, encoding="utf-8")
    print("\n" + note)
    if len(flips):
        print(flips.to_string(index=False))


if __name__ == "__main__":
    main()
