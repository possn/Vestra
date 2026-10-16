#!/usr/bin/env python3
"""Decide whether a fresh canonical market rebuild is needed today (UTC)."""
import json
import os
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def due(payload, today):
    if not isinstance(payload, dict):
        return True
    stamp = payload.get("generated_at")
    if not isinstance(stamp, str):
        return True
    try:
        observed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        return observed.tzinfo is None or observed.astimezone(timezone.utc).date() < today
    except ValueError:
        return True

def main():
    try:
        payload = json.loads((ROOT / "data/stocks.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        payload = {}
    needs_rebuild = due(payload, datetime.now(timezone.utc).date())
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as fh:
            fh.write(f"rebuild={'true' if needs_rebuild else 'false'}\n")
    print(f"Canonical rebuild recovery needed: {needs_rebuild}")
if __name__ == "__main__":
    main()
