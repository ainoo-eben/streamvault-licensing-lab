"""Rate-limited, cached, resumable TMDB API client with fetch ledger."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import requests
import yaml

CONFIG_PATH = Path("config.yaml")


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def api_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"Accept": "application/json"})
    return session


def fetch_json(session: requests.Session, url: str, params: dict[str, Any], retries: int, timeout: int) -> dict[str, Any]:
    last_error: Exception | None = None
    for _ in range(retries):
        response = session.get(url, params=params, timeout=timeout)
        if response.status_code == 200:
            return response.json()
        last_error = requests.HTTPError(f"{response.status_code} for {url}", response=response)
        time.sleep(1)
    raise last_error or RuntimeError(f"failed to fetch {url}")


def cache_response(cache_dir: Path, endpoint: str, tmdb_id: int, payload: dict[str, Any]) -> None:
    (cache_dir / endpoint).mkdir(parents=True, exist_ok=True)
    path = cache_dir / endpoint / f"{tmdb_id}.json"
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def main() -> None:
    config = load_config()
    print("fetch placeholder: implement TMDB pulls into data/raw/")


if __name__ == "__main__":
    main()
