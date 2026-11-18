"""Reconciliation and join-integrity assertions."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def assert_no_duplicate_films(frame: pd.DataFrame) -> None:
    duplicates = int(frame.duplicated(subset=["tmdb_id"]).sum())
    if duplicates:
        raise AssertionError(f"{duplicates} duplicate films found")


def assert_ledger_matches(ledger_path: Path, total_ids: int) -> None:
    pass


def main() -> None:
    print("checks placeholder: run reconciliation assertions")


if __name__ == "__main__":
    main()
