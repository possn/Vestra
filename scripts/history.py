"""
history.py — rolling daily score history per ticker.

Kept as a SEPARATE small file (data/history.json) rather than bloating
stocks.json, since stocks.json is rewritten wholesale every run and
history needs to accumulate across runs.

Format: {"AAPL": {"2026-08-14": 62.5, "2026-08-15": 61.0, ...}, ...}
Only the composite score is tracked (not every field) to keep this file
small — at ~550 tickers x 120 days x ~12 bytes/entry that's still well
under a megabyte, comfortably within GitHub's normal file-size handling
and the REST API's inline-content threshold.

Capped to MAX_DAYS trailing entries per ticker. Tickers that drop out of
the universe (delisted, fell out of the screener) keep their old history
until it ages out naturally — this is intentional: a stock that vanished
from the scan is still informative context if you're looking back.
"""
from __future__ import annotations

import datetime
import json
import logging
import os

log = logging.getLogger("history")

MAX_DAYS = 120


def load(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except Exception as e:
        log.warning("Could not load existing history at %s (%s) — starting fresh", path, e)
        return {}


def update(history: dict, rows: list[dict], today: str) -> dict:
    """rows: the list of scored-ticker dicts from run.py (same shape as
    written to stocks.json). Mutates and returns `history`."""
    for row in rows:
        score = row.get("score")
        if score is None or (isinstance(score, float) and score != score):  # None or NaN
            continue
        ticker = row["ticker"]
        series = history.setdefault(ticker, {})
        series[today] = score
        if len(series) > MAX_DAYS:
            for old_date in sorted(series.keys())[: len(series) - MAX_DAYS]:
                del series[old_date]
    return history


def save(history: dict, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(history, f, separators=(",", ":"))  # compact, this file is written daily forever
    log.info("Wrote history for %d tickers to %s", len(history), path)
