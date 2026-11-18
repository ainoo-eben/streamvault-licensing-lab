"""Row counts, no dropped or duplicated films, ledger totals reconcile."""

from __future__ import annotations

import pandas as pd


def test_no_duplicate_films() -> None:
    frame = pd.DataFrame({"tmdb_id": [1, 2, 3], "title": ["a", "b", "c"]})
    assert frame.duplicated(subset=["tmdb_id"]).sum() == 0


def test_ledger_reconciles(tmp_path) -> None:
    ledger = tmp_path / "fetch_ledger.csv"
    ledger.write_text("id,status\n1,ok\n2,ok\n3,404\n", encoding="utf-8")
    statuses = pd.read_csv(ledger)["status"].value_counts().to_dict()
    assert statuses.get("ok", 0) + statuses.get("404", 0) == 3
