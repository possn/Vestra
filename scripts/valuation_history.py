"""Rolling daily valuation snapshots used for self-relative valuation context.

The app should not pretend that one cross-sectional multiple is a full valuation
history. This file accumulates the multiples that the scanner actually observed
on each daily run. Once enough observations exist, the UI can compare today's
multiple with the stock's own observed median.

Format:
{
  "AAPL": {
    "2026-08-14": {"pe": 28.1, "fpe": 25.3, "pb": 42.0, "ev": 20.4},
    ...
  }
}
"""
from __future__ import annotations

import json
import logging
import os

log = logging.getLogger("valuation_history")
MAX_DAYS = 365


def load(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception as e:
        log.warning("Could not load valuation history at %s (%s) — starting fresh", path, e)
        return {}


def update(history: dict, rows: list[dict], today: str) -> dict:
    fields = {
        "pe": "trailing_pe",
        "fpe": "forward_pe",
        "pb": "price_to_book",
        "ev": "enterprise_to_ebitda",
    }
    for row in rows:
        if row.get("quote_type") == "ETF":
            continue
        snapshot = {}
        for short, field in fields.items():
            v = row.get(field)
            if isinstance(v, (int, float)) and v == v and v > 0:
                snapshot[short] = round(float(v), 4)
        if not snapshot:
            continue
        ticker = row["ticker"]
        series = history.setdefault(ticker, {})
        series[today] = snapshot
        if len(series) > MAX_DAYS:
            for old_date in sorted(series)[: len(series) - MAX_DAYS]:
                del series[old_date]
    return history


def save(history: dict, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(history, f, separators=(",", ":"))
    log.info("Wrote valuation history for %d tickers to %s", len(history), path)
