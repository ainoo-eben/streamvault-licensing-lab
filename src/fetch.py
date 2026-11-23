"""Rate-limited, cached, resumable TMDB API client with per-id fetch ledger."""

from __future__ import annotations

import csv
import json
import os
import time
from pathlib import Path
from typing import Any

import requests
import yaml

CONFIG_PATH = Path("config.yaml")
RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")
INPUT_CSV = Path("data/input/id_list.csv")
SAMPLE_INPUT_CSV = Path("data/input/id_sample.csv")
LEDGER_PATH = PROCESSED_DIR / "fetch_ledger.csv"
BASE_URL = "https://api.themoviedb.org/3"


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    """Load pipeline settings from the project's YAML configuration."""
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_api_key(config: dict[str, Any]) -> str:
    """Read the TMDB key from the environment, then fall back to the local .env."""
    env_name = config["tmdb"]["api_key_env"]
    key = os.environ.get(env_name)
    if not key:
        env_file = Path(".env")
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                if "=" in line and not line.strip().startswith("#"):
                    k, v = line.split("=", 1)
                    if k.strip() == env_name:
                        key = v.strip()
                        break
    if not key or key == "your_key_here":
        raise RuntimeError(f"Set {env_name} in .env (copy from .env.example)")
    return key


def resolve_input_path(config: dict[str, Any]) -> Path:
    """Use the configured candidate file, or the tracked sample if it is missing."""
    configured = Path(config.get("data", {}).get("input_csv", INPUT_CSV))
    if configured.is_file():
        return configured
    # Keep a missing custom path visible instead of silently substituting sample data.
    if configured == INPUT_CSV and SAMPLE_INPUT_CSV.is_file():
        return SAMPLE_INPUT_CSV
    raise FileNotFoundError(
        f"Input CSV not found: {configured}. Add the candidate list or restore "
        f"{SAMPLE_INPUT_CSV} for a sample run."
    )


def read_input_rows(path: Path = INPUT_CSV) -> list[tuple[Any, str]]:
    """Read each CSV data row as (positive numeric TMDB id or None, original text).

    DictReader consumes the column header separately; invalid values are retained
    with a None id so the fetch ledger can account for every data row.
    """
    rows: list[tuple[Any, str]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            raw = (row.get("tmdb_id") or "").strip()
            if not raw:
                rows.append((None, raw))
                continue
            try:
                value = int(float(raw))
            except ValueError:
                rows.append((None, raw))
                continue
            if value <= 0:
                rows.append((None, raw))
                continue
            rows.append((value, raw))
    return rows


def _sleep_rate_limit(config: dict[str, Any]) -> None:
    """Wait long enough to stay under the configured requests-per-10-seconds cap."""
    per_10s = config["tmdb"].get("rate_limit_per_10s", 35)
    delay = 10.0 / max(per_10s, 1)
    time.sleep(delay)


def fetch_one(session: requests.Session, url: str, params: dict[str, Any],
              retries: int, timeout: int) -> tuple[int, Any]:
    """Request one endpoint; retry network, rate-limit, and server failures."""
    last_status = 0
    for attempt in range(retries):
        try:
            response = session.get(url, params=params, timeout=timeout)
        except requests.RequestException:
            time.sleep(2 ** attempt)
            continue
        last_status = response.status_code
        if response.status_code == 200:
            return 200, response.json()
        if response.status_code == 404:
            return 404, None
        if response.status_code == 429 or response.status_code >= 500:
            # Honor TMDB's requested delay; otherwise use exponential backoff.
            retry_after = response.headers.get("Retry-After")
            wait = float(retry_after) if retry_after else 2 ** attempt
            time.sleep(wait)
            continue
        return response.status_code, None
    return last_status or 0, None


def cache_path(endpoint: str, tmdb_id: int) -> Path:
    """Build the raw-JSON path for one TMDB endpoint and movie id."""
    return RAW_DIR / endpoint / f"{tmdb_id}.json"


def is_cached(tmdb_id: int) -> bool:
    """Only treat a movie as cached when both details and credits are present."""
    return cache_path("details", tmdb_id).exists() and cache_path("credits", tmdb_id).exists()


def fetch_movie(session: requests.Session, tmdb_id: int, api_key: str,
               config: dict[str, Any]) -> tuple[str, dict[str, Any] | None, dict[str, Any] | None]:
    """Fetch details and credits, returning a ledger status and both payloads.

    A film is successful only when both endpoints return data. TMDB may redirect
    an obsolete id to another id; that response is kept but marked redirected.
    """
    params = {"api_key": api_key}
    timeout = config["tmdb"].get("timeout_s", 30)
    retries = config["tmdb"].get("retries", 3)

    _sleep_rate_limit(config)
    status, details = fetch_one(session, f"{BASE_URL}/movie/{tmdb_id}", params, retries, timeout)
    if status == 404:
        return "404", None, None
    if status != 200 or not details:
        return "failed", None, None

    redirected = details.get("id") != tmdb_id

    _sleep_rate_limit(config)
    c_status, credits = fetch_one(session, f"{BASE_URL}/movie/{tmdb_id}/credits", params, retries, timeout)
    if c_status == 404:
        return "404", details, None
    if c_status != 200 or not credits:
        return "failed", details, None

    if redirected:
        return "redirected", details, credits
    return "ok", details, credits


def main() -> None:
    """Fetch uncached unique ids and write one status row per input data row."""
    config = load_config()
    api_key = load_api_key(config)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    (RAW_DIR / "details").mkdir(parents=True, exist_ok=True)
    (RAW_DIR / "credits").mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    input_rows = read_input_rows(resolve_input_path(config))
    seen: set[int] = set()
    ledger_rows: list[dict[str, Any]] = []

    # Reuse a session for connection pooling and send JSON-oriented requests.
    session = requests.Session()
    session.headers.update({"Accept": "application/json"})

    for tmdb_id, raw in input_rows:
        if tmdb_id is None:
            ledger_rows.append({"id": raw, "status": "invalid"})
            continue
        if tmdb_id in seen:
            ledger_rows.append({"id": tmdb_id, "status": "duplicate"})
            continue
        seen.add(tmdb_id)

        # A partial cache is not enough: missing details or credits must be fetched.
        if is_cached(tmdb_id):
            ledger_rows.append({"id": tmdb_id, "status": "ok"})
            continue

        status, details, credits = fetch_movie(session, tmdb_id, api_key, config)

        if status in ("ok", "redirected"):
            with cache_path("details", tmdb_id).open("w", encoding="utf-8") as f:
                json.dump(details, f, indent=2)
            with cache_path("credits", tmdb_id).open("w", encoding="utf-8") as f:
                json.dump(credits, f, indent=2)

        ledger_rows.append({"id": tmdb_id, "status": status})

    # Keep invalid, duplicate, failed, and successful rows so list totals reconcile.
    with LEDGER_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["id", "status"])
        writer.writeheader()
        writer.writerows(ledger_rows)

    counts: dict[str, int] = {}
    for row in ledger_rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    print(f"fetch complete: {len(ledger_rows)} rows -> {counts}")


if __name__ == "__main__":
    main()
