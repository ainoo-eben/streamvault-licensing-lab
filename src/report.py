"""Shortlist support reports, pipeline timing, and data-quality diagnostics."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

try:
    from src.analysis import compare_windows
    from src.fetch import read_input_rows, resolve_input_path
    from src.metrics import financial_data_available
except ModuleNotFoundError:
    from analysis import compare_windows
    from fetch import read_input_rows, resolve_input_path
    from metrics import financial_data_available

CONFIG_PATH = Path("config.yaml")
OUTPUT_DIR = Path("outputs")
LOG_PATH = OUTPUT_DIR / "run_log.txt"
PROCESSED_DIR = Path("data/processed")
RAW_DIR = Path("data/raw")


def data_quality_report(
    config_path: Path = CONFIG_PATH,
    input_path: Path | None = None,
    ledger_path: Path | None = None,
    processed_dir: Path | None = None,
    raw_dir: Path | None = None,
) -> str:
    with config_path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    input_path = input_path or resolve_input_path(config)
    processed_dir = processed_dir or Path(
        config["data"].get("processed_dir", PROCESSED_DIR)
    )
    raw_dir = raw_dir or Path(config["data"].get("raw_dir", RAW_DIR))
    ledger_path = ledger_path or processed_dir / "fetch_ledger.csv"

    input_rows = read_input_rows(input_path)
    requested_ids = {
        tmdb_id for tmdb_id, _ in input_rows if tmdb_id is not None
    }
    ledger = pd.read_csv(ledger_path, dtype={"id": str, "status": str})
    ledger_statuses = ledger["status"].value_counts().to_dict()
    films = pd.read_parquet(processed_dir / "films.parquet")
    credits = pd.read_parquet(processed_dir / "credits.parquet")
    analysis = pd.read_parquet(processed_dir / "analysis_table.parquet")

    lines = ["Data quality report", "===================="]
    lines.append(f"Input rows: {len(input_rows)} ({input_path})")
    lines.append(f"Fetch ledger rows: {len(ledger)}; statuses: {ledger_statuses}")
    if len(ledger) != len(input_rows):
        lines.append("  FLAG: input row count does not match ledger row count")

    lines.append(f"Fetched films: {len(films)}")
    lines.append(f"Credit rows: {len(credits)}")
    lines.append(f"Analysis rows: {len(analysis)}")
    if len(analysis) != len(films):
        lines.append("  FLAG: analysis table row count differs from film table")

    excluded_financials = int((~financial_data_available(films)).sum())
    lines.append(
        f"Films excluded from financial metrics (missing or non-positive budget/revenue): "
        f"{excluded_financials}"
    )
    lines.append(
        f"Missing budget: {int(films['budget'].isna().sum())}; "
        f"missing revenue: {int(films['revenue'].isna().sum())}"
    )
    non_positive_money = int(
        (
            films["budget"].le(0).fillna(False)
            | films["revenue"].le(0).fillna(False)
        ).sum()
    )
    lines.append(f"Films with non-positive budget or revenue: {non_positive_money}")
    lines.append(f"Missing release dates: {int(films['release_date'].isna().sum())}")
    duplicate_ids = int(films.duplicated(subset=["tmdb_id"]).sum())
    lines.append(f"Duplicate film ids: {duplicate_ids}")
    if duplicate_ids:
        lines.append("  FLAG: duplicate films present")

    raw_detail_ids = {
        int(path.stem)
        for path in (raw_dir / "details").glob("*.json")
        if path.stem.isdigit()
    }
    raw_credit_ids = {
        int(path.stem)
        for path in (raw_dir / "credits").glob("*.json")
        if path.stem.isdigit()
    }
    raw_detail_count = len(raw_detail_ids)
    raw_credit_count = len(raw_credit_ids)
    current_detail_count = len(raw_detail_ids & requested_ids)
    current_credit_count = len(raw_credit_ids & requested_ids)
    stale_cache_count = len(raw_detail_ids - requested_ids) + len(
        raw_credit_ids - requested_ids
    )
    lines.append(
        f"Raw cache files: details={raw_detail_count} "
        f"({current_detail_count} current-list), credits={raw_credit_count} "
        f"({current_credit_count} current-list)"
    )
    lines.append(
        f"Stale cached JSON files excluded from this run: {stale_cache_count}"
    )
    if current_detail_count != len(films) or current_credit_count != len(films):
        lines.append("  FLAG: current-list raw cache counts differ from the film table")

    comparisons = compare_windows(analysis, config)
    lines.append("Film-weighted hit rates by window:")
    for row in comparisons.itertuples(index=False):
        if row.n_franchise_financially_eligible:
            franchise_rate = f"{row.franchise_hit_rate:.1%}"
        else:
            franchise_rate = "n/a"
        if row.n_standalone_financially_eligible:
            standalone_rate = f"{row.standalone_hit_rate:.1%}"
        else:
            standalone_rate = "n/a"
        lines.append(
            f"  {row.window}: franchise={franchise_rate} "
            f"({row.n_franchise_hits}/{row.n_franchise_financially_eligible} hits; "
            f"{row.n_franchise_financially_eligible}/{row.n_franchise_films} "
            f"financially eligible), "
            f"standalone={standalone_rate} "
            f"({row.n_standalone_hits}/{row.n_standalone_financially_eligible} hits; "
            f"{row.n_standalone_financially_eligible}/{row.n_standalone_films} "
            f"financially eligible)"
        )
        if (
            row.n_franchise_financially_eligible
            and row.n_standalone_financially_eligible
        ):
            leader = (
                "franchise"
                if row.franchise_hit_rate > row.standalone_hit_rate
                else "standalone"
            )
            lines.append(f"    Higher film hit rate: {leader}")

    return "\n".join(lines)


def write_run_log(
    runtime_seconds: float,
    log_path: Path = LOG_PATH,
    processed_dir: Path = PROCESSED_DIR,
    input_path: Path | None = None,
) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if input_path is None:
        with CONFIG_PATH.open("r", encoding="utf-8") as handle:
            config = yaml.safe_load(handle)
        input_path = resolve_input_path(config)
    input_row_count = len(read_input_rows(input_path))
    films = pd.read_parquet(processed_dir / "films.parquet")
    credits = pd.read_parquet(processed_dir / "credits.parquet")
    analysis = pd.read_parquet(processed_dir / "analysis_table.parquet")
    ledger = pd.read_csv(processed_dir / "fetch_ledger.csv")
    status_counts = ledger["status"].value_counts().to_dict()
    log_path.write_text(
        "\n".join(
            [
                "StreamVault Licensing run log",
                "=============================",
                f"Rows: input={input_row_count}, ledger={len(ledger)}, "
                f"films={len(films)}, "
                f"credits={len(credits)}, analysis_table={len(analysis)}",
                f"Fetch statuses: {status_counts}",
                f"Total pipeline runtime: {runtime_seconds:.2f}s",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report = data_quality_report()
    report_path = OUTPUT_DIR / "data_quality_report.txt"
    report_path.write_text(report, encoding="utf-8")
    print(report)
    print(f"\nData quality report written to {report_path}")


if __name__ == "__main__":
    main()
