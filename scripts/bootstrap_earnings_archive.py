#!/usr/bin/env python3
"""Bootstrap a verified earnings archive from the canonical index, without network calls.

This is deliberately independent of the Yahoo refresh: it guarantees an initial
archive is published even when the expensive data collection is delayed.
"""
from __future__ import annotations

import json
from pathlib import Path

try:
    from scripts.earnings_archive import ARCHIVE_PATH, save_archive
except ModuleNotFoundError:
    from earnings_archive import ARCHIVE_PATH, save_archive

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "data" / "stocks-index.json"


def verified_rows(stocks):
    for row in stocks:
        if not isinstance(row, dict):
            continue
        actual = row.get("analyst_latest_eps_actual")
        if isinstance(actual, bool) or not isinstance(actual, (int, float)):
            continue
        if row.get("analyst_latest_earnings_date"):
            yield row


def main():
    payload = json.loads(INDEX.read_text(encoding="utf-8"))
    rows = list(verified_rows(payload.get("stocks") or []))
    archive = save_archive(rows)
    print(json.dumps({
        "archive": str(ARCHIVE_PATH.relative_to(ROOT)),
        "verified_input_rows": len(rows),
        "archived_events": len(archive["events"]),
    }))
    if not archive["events"]:
        raise RuntimeError("Archive has no verified earnings; investigate source coverage before publishing")


if __name__ == "__main__":
    main()
