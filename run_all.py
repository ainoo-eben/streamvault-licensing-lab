"""One command, top to bottom: fetch -> tidy -> checks -> analysis -> report."""

from __future__ import annotations

import subprocess
import sys
import time

from src.report import write_run_log

STEPS = [
    "src/fetch.py",
    "src/tidy.py",
    "src/checks.py",
    "src/analysis.py",
    "src/talent.py",
    "src/report.py",
]


def main() -> None:
    """Run each pipeline stage in order, stopping immediately if one fails."""
    start = time.perf_counter()
    for step in STEPS:
        print(f"\n=== {step} ===")
        result = subprocess.run([sys.executable, step], check=False)
        if result.returncode != 0:
            print(f"FAILED at {step} (exit {result.returncode})")
            sys.exit(result.returncode)
    # Log runtime only after every stage succeeds and its output tables exist.
    elapsed = time.perf_counter() - start
    write_run_log(elapsed)
    print(f"\nAll steps completed in {elapsed:.2f}s")


if __name__ == "__main__":
    main()
