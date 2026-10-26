#!/usr/bin/env python3
"""Detect missing closed scanner slots from immutable published archives.

Diagnostic only: never generates or fills past observations.
"""
import argparse
import json
import os
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

def slot_publication_summary(now, archive, lookback_days=3):
    """Archive-backed publication observability, not an execution-history claim.

    Only closed scheduled windows enter the denominator. Without GitHub Actions
    run data an absent archive cannot distinguish skipped, failed or deferred runs.
    """
    if now.tzinfo is None:
        raise ValueError("timezone-aware clock required")
    now = now.astimezone(timezone.utc)
    missing = missing_closed_slots(now, archive, lookback_days)
    missing_keys = {(item["date"], item["slot"]) for item in missing}
    published = []
    for offset in range(max(0, lookback_days) + 1):
        day = (now - timedelta(days=offset)).date()
        if day.weekday() == 6:
            continue
        for slot, hour in enumerate(SLOT_HOURS):
            if day.weekday() == 5 and slot >= 2:
                continue
            scheduled = datetime(day.year, day.month, day.day, hour, 10, tzinfo=timezone.utc)
            if now <= scheduled + timedelta(hours=3, minutes=25):
                continue
            key = (day.isoformat(), slot)
            if key in missing_keys:
                continue
            path = archive / str(day.year) / "slots" / f"{day.isoformat()}-slot{slot}.json"
            # This audit tests archive presence, not content validity or successful execution.
            if path.is_file():
                published.append({"date": key[0], "slot": slot})
    closed = len(published) + len(missing)
    return {
        "closed_expected_slots": closed,
        "published_archive_slots": len(published),
        "missing_archive_slots": len(missing),
        "archive_publication_pct": round(100 * len(published) / closed, 2) if closed else None,
        "execution_status": "not_observed",
        "missing_cause": "unknown_without_actions_run_evidence",
        "missing_closed_slots": missing,
    }

def actions_step_summary(summary):
    """Human-readable archive publication evidence for GitHub Actions."""
    expected = summary["closed_expected_slots"]
    published = summary["published_archive_slots"]
    missing = summary["missing_archive_slots"]
    pct = summary["archive_publication_pct"]
    coverage = "n/a" if pct is None else f"{pct:.2f}%"
    rows = [
        "### Pré-Breakout · publicação dos ciclos",
        "",
        "| Janela fechada prevista | Arquivo presente | Arquivo ausente | Taxa de publicação |",
        "|---:|---:|---:|---:|",
        f"| {expected} | {published} | {missing} | {coverage} |",
        "",
        "A presença de arquivo **não demonstra** que o scan executou com êxito. "
        "Um arquivo ausente não distingue execução omitida, falhada ou publicação adiada.",
    ]
    if missing:
        rows.extend(["", "**Ciclos sem arquivo:**"])
        rows.extend(f"- {item['date']} · slot {item['slot']} ({item['scheduled_utc']})"
                    for item in summary["missing_closed_slots"])
    return "\\n".join(rows) + "\\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=ROOT / "data/prebreakout-history")
    parser.add_argument("--lookback-days", type=int, default=3)
    args = parser.parse_args()
    now = datetime.now(timezone.utc)
    summary = slot_publication_summary(now, args.archive, args.lookback_days)
    missing = summary["missing_closed_slots"]
    print(json.dumps({"checked_at": now.isoformat(), **summary}))
    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        with open(step_summary, "a", encoding="utf-8") as output:
            output.write(actions_step_summary(summary))
    for item in missing:
        print(f"::warning::Prebreakout slot not published: {item['date']} slot{item['slot']}")
    # Diagnostic only: do not fail the scanning workflow or fabricate older slots.
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
