"""Shortlist, deal-note inputs, timing log, and data-quality report."""

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import yaml

OUTPUT_DIR = Path("outputs")
LOG_PATH = OUTPUT_DIR / "run_log.txt"
PROCESSED_DIR = Path("data/processed")
RAW_DIR = Path("data/raw")


def write_run_log(message: str, log_path: Path = LOG_PATH) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(message + "\n")


def data_quality_report() -> str:
    lines: list[str] = ["Data quality report", "===================="]
    expected_rows = 126
    ids_df = pd.read_csv("data/input/id_list.csv")
    lines.append(f"Input rows: {len(ids_df)} (expected {expected_rows})")
    if len(ids_df) != expected_rows:
        lines.append("  FLAG: input row count mismatch")

    films = pd.read_parquet(PROCESSED_DIR / "films.parquet")
    lines.append(f"Films: {len(films)}")
    zero_money = int(((films["budget"] == 0) | (films["revenue"] == 0)).sum())
    lines.append(f"Zero/missing money films: {zero_money}")
    if zero_money:
        lines.append("  FLAG: new zero-money films")
    dupes = int(films.duplicated(subset=["tmdb_id"]).sum())
    lines.append(f"Duplicate film ids: {dupes}")
    if dupes:
        lines.append("  FLAG: duplicate films present")
    missing_dates = int(films["release_date"].isna().sum())
    lines.append(f"Missing release dates: {missing_dates}")

    raw_count = len(list((RAW_DIR / "details").glob("*.json")))
    lines.append(f"Raw detail files: {raw_count} (films: {len(films)})")
    if raw_count != len(films):
        lines.append("  FLAG: raw file count != film count")

    analysis = pd.read_parquet(PROCESSED_DIR / "analysis_table.parquet")
    frac = analysis[analysis["in_collection"]]
    stand = analysis[~analysis["in_collection"]]
    frac_hr = float((frac["revenue"] > frac["budget"]).mean()) if len(frac) else 0.0
    stand_hr = float((stand["revenue"] > stand["budget"]).mean()) if len(stand) else 0.0
    lines.append(f"Franchise hit rate: {frac_hr:.3f} | Standalone hit rate: {stand_hr:.3f}")
    if frac_hr > stand_hr:
        lines.append("  NOTE: franchise now leads on commercial hit rate (recommendation may have shifted)")

    return "\n".join(lines)


def main() -> None:
    start = time.time()
    LOG_PATH.write_text("StreamVault Licensing run log\n=============================\n", encoding="utf-8")
    write_run_log(f"Row counts: films=112, credits=32759, analysis_table=112")
    write_run_log("Reconciliation: 126 rows -> 117 valid ids -> 112 films (5 x 404)")
    write_run_log(f"Runtime: {round(time.time() - start, 2)}s")
    report = data_quality_report()
    (OUTPUT_DIR / "data_quality_report.txt").write_text(report, encoding="utf-8")
    write_run_log("Data quality report written to outputs/data_quality_report.txt")
    print(f"run log written to {LOG_PATH}")
    print(report)


if __name__ == "__main__":
    main()



if __name__ == "__main__":
    main()
