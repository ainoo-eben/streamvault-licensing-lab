import pandas as pd
import yaml

from src.report import data_quality_report, write_run_log


def test_quality_report_and_run_log_use_current_input_counts(tmp_path) -> None:
    input_path = tmp_path / "ids.csv"
    input_path.write_text("tmdb_id\n1\nbad\n3\n", encoding="utf-8")
    processed_dir = tmp_path / "processed"
    raw_dir = tmp_path / "raw"
    (raw_dir / "details").mkdir(parents=True)
    (raw_dir / "credits").mkdir(parents=True)
    processed_dir.mkdir()
    ledger_path = processed_dir / "fetch_ledger.csv"
    pd.DataFrame(
        {"id": ["1", "bad", "3"], "status": ["ok", "invalid", "ok"]}
    ).to_csv(ledger_path, index=False)

    films = pd.DataFrame(
        [
            {
                "tmdb_id": 1,
                "title": "Known hit",
                "release_date": pd.Timestamp("2020-01-01"),
                "release_year": 2020,
                "collection_name": "Series",
                "in_collection": True,
                "budget": 100,
                "revenue": 200,
                "vote_count": 2000,
                "vote_average": 8.0,
            },
            {
                "tmdb_id": 2,
                "title": "Unknown cost",
                "release_date": pd.Timestamp("2020-01-01"),
                "release_year": 2020,
                "collection_name": "Series",
                "in_collection": True,
                "budget": 0,
                "revenue": 200,
                "vote_count": 2000,
                "vote_average": 8.0,
            },
            {
                "tmdb_id": 3,
                "title": "Standalone hit",
                "release_date": pd.Timestamp("2020-01-01"),
                "release_year": 2020,
                "collection_name": None,
                "in_collection": False,
                "budget": 100,
                "revenue": 200,
                "vote_count": 2000,
                "vote_average": 8.0,
            },
        ]
    )
    films.to_parquet(processed_dir / "films.parquet", index=False)
    pd.DataFrame(columns=["tmdb_id", "name"]).to_parquet(
        processed_dir / "credits.parquet", index=False
    )
    films.to_parquet(processed_dir / "analysis_table.parquet", index=False)
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "data": {
                    "input_csv": str(input_path),
                    "processed_dir": str(processed_dir),
                    "raw_dir": str(raw_dir),
                },
                "hit": {"min_votes": 1000, "min_rating": 7.0},
                "windows": {
                    "all_years": [1900, 2099],
                    "since_2000": [2000, 2099],
                },
                "franchise": {"min_entries_on_list": 2},
            }
        ),
        encoding="utf-8",
    )

    report = data_quality_report(
        config_path=config_path,
        input_path=input_path,
        ledger_path=ledger_path,
        processed_dir=processed_dir,
        raw_dir=raw_dir,
    )
    log_path = tmp_path / "run_log.txt"
    write_run_log(
        1.25,
        log_path=log_path,
        processed_dir=processed_dir,
        input_path=input_path,
    )

    assert "Input rows: 3" in report
    assert "Fetch ledger rows: 3" in report
    assert "Films excluded from financial metrics" in report
    assert "franchise=100.0% (1/1 hits; 1/2 financially eligible)" in report
    assert "standalone=100.0% (1/1 hits; 1/1 financially eligible)" in report
    assert "input=3, ledger=3, films=3, credits=0, analysis_table=3" in log_path.read_text()
    assert "Total pipeline runtime: 1.25s" in log_path.read_text()
