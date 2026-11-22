"""Director and actor signal with minimum-count rules."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

CONFIG_PATH = Path("config.yaml")
PROCESSED_DIR = Path("data/processed")
OUTPUT_DIR = Path("outputs/tables")


def load_config(path: Path = CONFIG_PATH) -> dict:
    with path.open() as f:
        return yaml.safe_load(f)


def talent_signal(credits: pd.DataFrame, films: pd.DataFrame,
                  min_films_director: int = 3, min_films_actor: int = 5,
                  m: int = 1000, c: float = 6.0) -> pd.DataFrame:
    film_lookup = films.set_index("tmdb_id")
    directors = credits[(credits["role"] == "crew") & (credits["job"] == "Director")]
    cast = credits[(credits["role"] == "cast") & (credits["cast_order"] == 0)]

    rows: list[dict] = []
    for label, subset, min_n in [("director", directors, min_films_director),
                                 ("actor", cast, min_films_actor)]:
        for name, grp in subset.groupby("name"):
            ids = grp["tmdb_id"].unique()
            if len(ids) < min_n:
                continue
            sub = film_lookup.loc[ids]
            avg_rating = float(sub["vote_average"].mean())
            hit_share = float((sub["revenue"] > sub["budget"]).mean())
            shrunk = (len(ids) / (len(ids) + 3)) * avg_rating + (3 / (len(ids) + 3)) * c
            rows.append({
                "name": name,
                "role": label,
                "n_films": len(ids),
                "avg_rating": round(avg_rating, 2),
                "hit_share": round(hit_share, 3),
                "shrunk_rating": round(shrunk, 2),
            })
    return pd.DataFrame(rows).sort_values(["role", "shrunk_rating"], ascending=[True, False])


def main() -> None:
    cfg = load_config()
    films = pd.read_parquet(PROCESSED_DIR / "films.parquet")
    credits = pd.read_parquet(PROCESSED_DIR / "credits.parquet")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out = talent_signal(
        credits, films,
        cfg["talent"]["min_films_director"],
        cfg["talent"]["min_films_actor"],
        cfg["adjusted_rating"]["m"],
        cfg["adjusted_rating"]["c"],
    )
    out.to_csv(OUTPUT_DIR / "talent_read.csv", index=False)
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
