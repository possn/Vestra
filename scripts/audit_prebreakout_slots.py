#!/usr/bin/env python3
"""Detect missing closed scanner slots from immutable published archives.

Diagnostic only: never generates or fills past observations.
"""
import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SLOT_HOURS = (2, 8, 14, 20)

def missing_closed_slots(now, archive, lookback_days=3):
    if now.tzinfo is None:
        raise ValueError("timezone-aware clock required")
    now = now.astimezone(timezone.utc)
    misses = []
    for offset in range(max(0, lookback_days) + 1):
        day = (now - timedelta(days=offset)).date()
        # Sunday is closed. Saturday has two scheduled catch-up scans
        # (02:10 and 08:10 UTC) to capture the completed Friday US session.
        if day.weekday() == 6:
            continue
        for slot, hour in enumerate(SLOT_HOURS):
            if day.weekday() == 5 and slot >= 2:
                continue
            start = datetime(day.year, day.month, day.day, hour, 10, tzinfo=timezone.utc)
            # Allow the existing catch-up window through hour+3:35.
            recovery_end = start + timedelta(hours=3, minutes=25)
            if now <= recovery_end:
                continue
            path = archive / str(day.year) / "slots" / f"{day.isoformat()}-slot{slot}.json"
            if not path.is_file():
                misses.append({"date": day.isoformat(), "slot": slot,
                               "scheduled_utc": start.isoformat()})
    return sorted(misses, key=lambda item: (item["date"], item["slot"]))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=ROOT / "data/prebreakout-history")
    parser.add_argument("--lookback-days", type=int, default=3)
    args = parser.parse_args()
    now = datetime.now(timezone.utc)
    missing = missing_closed_slots(now, args.archive, args.lookback_days)
    print(json.dumps({"checked_at": now.isoformat(), "missing_closed_slots": missing}))
    for item in missing:
        print(f"::warning::Prebreakout slot not published: {item['date']} slot{item['slot']}")
    # Diagnostic only: do not fail the scanning workflow or fabricate older slots.
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
