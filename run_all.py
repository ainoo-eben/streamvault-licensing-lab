"""One command, top to bottom: fetch -> tidy -> checks -> analysis -> report."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

STEPS = [
    "src/fetch.py",
    "src/tidy.py",
    "src/checks.py",
    "src/analysis.py",
    "src/talent.py",
    "src/report.py",
]


def main() -> None:
    start = time.time()
    for step in STEPS:
        print(f"\n=== {step} ===")
        result = subprocess.run([sys.executable, step], check=False)
        if result.returncode != 0:
            print(f"FAILED at {step} (exit {result.returncode})")
            sys.exit(result.returncode)
    elapsed = round(time.time() - start, 2)
    print(f"\nAll steps completed in {elapsed}s")


if __name__ == "__main__":
    main()
