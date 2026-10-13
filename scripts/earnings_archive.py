"""Persistent, provenance-aware earnings event history, separate from startup payload."""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

ARCHIVE_PATH = Path(__file__).resolve().parents[1] / "data" / "earnings-events.json"
FIELDS = ("analyst_latest_eps_estimate", "analyst_latest_eps_actual", "analyst_latest_eps_surprise_pct")


def archive_rows(existing: dict, stocks: list[dict], today: date | None = None) -> dict:
    today = today or date.today()
    cutoff = today - timedelta(days=730)
    records = {}
    for event in existing.get("events", []):
        if not isinstance(event, dict):
            continue
        ticker, day = event.get("ticker"), event.get("date")
        try:
            valid = date.fromisoformat(str(day))
        except (TypeError, ValueError):
            continue
        if ticker and cutoff <= valid <= today and event.get("kind") == "earnings":
            records[(ticker, day)] = dict(event)
    for stock in stocks:
        if not isinstance(stock, dict):
            continue
        ticker = str(stock.get("ticker") or "").upper().strip()
        day = str(stock.get("analyst_latest_earnings_date") or "")[:10]
        try:
            valid = date.fromisoformat(day)
        except ValueError:
            continue
        if not ticker or not cutoff <= valid <= today:
            continue
        key = (ticker, day)
        previous = records.get(key, {})
        event = {
            "kind": "earnings", "ticker": ticker, "date": day,
            "name": str(stock.get("name") or previous.get("name") or ticker),
            "source": str(stock.get("earnings_source") or previous.get("source") or "stocks-index:analyst_latest_earnings_date"),
        }
        for field in FIELDS:
            value = stock.get(field)
            if isinstance(value, (float, int)) and not isinstance(value, bool):
                event[field] = value
            elif field in previous:
                event[field] = previous[field]
        records[key] = event
    events = sorted(records.values(), key=lambda e: (e["date"], e["ticker"]))
    return {"schema": "vestra_earnings_events_v1", "events": events}


def save_archive(stocks: list[dict], path: Path = ARCHIVE_PATH, today: date | None = None) -> dict:
    try:
        old = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        old = {}
    snapshot = archive_rows(old, stocks, today)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    return snapshot
