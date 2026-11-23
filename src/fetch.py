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
LEDGER_PATH = PROCESSED_DIR / "fetch_ledger.csv"
BASE_URL = "https://api.themoviedb.org/3"


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_api_key(config: dict[str, Any]) -> str:
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


def read_input_rows(path: Path = INPUT_CSV) -> list[tuple[Any, str]]:
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
    per_10s = config["tmdb"].get("rate_limit_per_10s", 35)
    delay = 10.0 / max(per_10s, 1)
    time.sleep(delay)


def fetch_one(session: requests.Session, url: str, params: dict[str, Any],
              retries: int, timeout: int) -> tuple[int, Any]:
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
            retry_after = response.headers.get("Retry-After")
            wait = float(retry_after) if retry_after else 2 ** attempt
            time.sleep(wait)
            continue
        return response.status_code, None
    return last_status or 0, None


def cache_path(endpoint: str, tmdb_id: int) -> Path:
    return RAW_DIR / endpoint / f"{tmdb_id}.json"


def is_cached(tmdb_id: int) -> bool:
    return cache_path("details", tmdb_id).exists() and cache_path("credits", tmdb_id).exists()


def fetch_movie(session: requests.Session, tmdb_id: int, api_key: str,
               config: dict[str, Any]) -> tuple[str, dict[str, Any] | None, dict[str, Any] | None]:
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
    config = load_config()
    api_key = load_api_key(config)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    (RAW_DIR / "details").mkdir(parents=True, exist_ok=True)
    (RAW_DIR / "credits").mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    input_rows = read_input_rows()
    seen: set[int] = set()
    ledger_rows: list[dict[str, Any]] = []

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
