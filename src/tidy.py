"""Flatten nested TMDB JSON responses into clean tables with flags."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


def details_to_frame(raw_dir: Path) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    for path in sorted((raw_dir / "details").glob("*.json")):
        pass
    return pd.DataFrame(records)


def credits_to_frame(raw_dir: Path) -> pd.DataFrame:
    return pd.DataFrame()


def main() -> None:
    print("tidy placeholder: flatten cached JSON into data/processed/")


if __name__ == "__main__":
    main()
