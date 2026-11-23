"""Flatten nested TMDB JSON responses into clean tables with flags."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

try:
    from src.fetch import load_config, read_input_rows, resolve_input_path
except ModuleNotFoundError:
    from fetch import load_config, read_input_rows, resolve_input_path

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")

FILM_FIELDS = [
    "id", "title", "release_date", "budget", "revenue",
    "vote_average", "vote_count", "runtime", "status",
    "original_language", "adult",
]


def _load_json_dir(
    directory: Path, requested_ids: set[int] | None = None
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    requested_names = (
        {str(tmdb_id) for tmdb_id in requested_ids}
        if requested_ids is not None
        else None
    )
    for path in sorted(directory.glob("*.json")):
        if requested_names is not None and path.stem not in requested_names:
            continue
        with path.open("r", encoding="utf-8") as handle:
            records.append(json.load(handle))
    return records


def build_films(
    details_dir: Path = RAW_DIR / "details",
    requested_ids: set[int] | None = None,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for movie in _load_json_dir(details_dir, requested_ids):
        collection = movie.get("belongs_to_collection")
        rows.append({
            "tmdb_id": movie.get("id"),
            "title": movie.get("title"),
            "release_date": movie.get("release_date"),
            "budget": movie.get("budget"),
            "revenue": movie.get("revenue"),
            "vote_average": movie.get("vote_average"),
            "vote_count": movie.get("vote_count"),
            "runtime": movie.get("runtime"),
            "status": movie.get("status"),
            "original_language": movie.get("original_language"),
            "adult": movie.get("adult"),
            "in_collection": collection is not None,
            "collection_name": collection.get("name") if isinstance(collection, dict) else None,
            "collection_id": collection.get("id") if isinstance(collection, dict) else None,
            "genre_count": len(movie.get("genres") or []),
            "genres": ", ".join(g.get("name", "") for g in (movie.get("genres") or [])),
        })
    frame = pd.DataFrame(rows)
    frame["release_date"] = pd.to_datetime(frame["release_date"], errors="coerce")
    frame["release_year"] = frame["release_date"].dt.year
    return frame


def build_credits(
    credits_dir: Path = RAW_DIR / "credits",
    requested_ids: set[int] | None = None,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for payload in _load_json_dir(credits_dir, requested_ids):
        tmdb_id = payload.get("id")
        for person in payload.get("cast", []) or []:
            rows.append({
                "tmdb_id": tmdb_id,
                "person_id": person.get("id"),
                "name": person.get("name"),
                "role": "cast",
                "job": None,
                "character": person.get("character"),
                "cast_order": person.get("order"),
            })
        for person in payload.get("crew", []) or []:
            rows.append({
                "tmdb_id": tmdb_id,
                "person_id": person.get("id"),
                "name": person.get("name"),
                "role": "crew",
                "job": person.get("job"),
                "character": None,
                "cast_order": None,
            })
    return pd.DataFrame(rows)


def build_analysis_table(films: pd.DataFrame, credits: pd.DataFrame) -> pd.DataFrame:
    directors = credits[(credits["role"] == "crew") & (credits["job"] == "Director")]
    director_counts = directors.groupby("tmdb_id").size().rename("director_count")
    cast_counts = credits[credits["role"] == "cast"].groupby("tmdb_id").size().rename("cast_count")
    out = films.merge(director_counts, on="tmdb_id", how="left")
    out = out.merge(cast_counts, on="tmdb_id", how="left")
    out["director_count"] = out["director_count"].fillna(0).astype(int)
    out["cast_count"] = out["cast_count"].fillna(0).astype(int)
    return out


def main() -> None:
    config = load_config()
    input_rows = read_input_rows(resolve_input_path(config))
    requested_ids = {tmdb_id for tmdb_id, _ in input_rows if tmdb_id is not None}
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    films = build_films(requested_ids=requested_ids)
    credits = build_credits(requested_ids=requested_ids)
    analysis_table = build_analysis_table(films, credits)
    films.to_parquet(PROCESSED_DIR / "films.parquet", index=False)
    credits.to_parquet(PROCESSED_DIR / "credits.parquet", index=False)
    analysis_table.to_parquet(PROCESSED_DIR / "analysis_table.parquet", index=False)
    print(f"films: {len(films)} rows, credits: {len(credits)} rows, analysis_table: {len(analysis_table)} rows")
    print(f"written to {PROCESSED_DIR}")


if __name__ == "__main__":
    main()
