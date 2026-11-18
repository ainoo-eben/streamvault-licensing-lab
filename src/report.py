"""Shortlist, deal-note inputs, and timing log."""

from __future__ import annotations

from pathlib import Path


def write_run_log(log_path: Path, message: str) -> None:
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(message + "\n")


def main() -> None:
    print("report placeholder: write shortlist and run_log.txt")


if __name__ == "__main__":
    main()
