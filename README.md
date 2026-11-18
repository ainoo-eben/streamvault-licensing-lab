# StreamVault Licensing

ML title-licensing pipeline written for Adjoa.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and add your TMDB API key:

```
copy .env.example .env
```

Edit `data/input/id_list.csv` with the TMDB ids to process (the only file you swap each cycle).

## One-command run

```bash
make all
```

This runs `fetch -> tidy -> checks -> metrics -> analysis -> talent -> report`
top to bottom and writes `data/processed/`, `outputs/`, and `docs/`.

## What each step does

- `src/fetch.py` - rate-limited, cached, resumable TMDB client + fetch ledger
- `src/tidy.py` - nested JSON to flat tables, cleaning rules, flags
- `src/checks.py` - reconciliation + join-integrity assertions
- `src/metrics.py` - hit rate, adjusted rating
- `src/analysis.py` - franchise vs standalone, both windows, sensitivity runs
- `src/talent.py` - director/actor signal with minimum-count rules
- `src/report.py` - shortlist, deal-note inputs, timing log

All tunable choices live in `config.yaml`.
