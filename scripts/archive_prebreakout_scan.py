#!/usr/bin/env python3
"""Archive the first *published* prebreakout scan per UTC day, never rewriting history."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CURRENT=ROOT/"data/prebreakout-signals.json"
ARCHIVE=ROOT/"data/prebreakout-history"

def archive(payload:dict, root:Path=ARCHIVE)->Path:
    if payload.get("schema")!="vestra_prebreakout_v1" or not isinstance(payload.get("signals"),list):
        raise ValueError("invalid scanner payload")
    when=datetime.fromisoformat(str(payload["generated_at"]).replace("Z","+00:00"))
    if when.tzinfo is None:raise ValueError("generated_at must include timezone")
    day=when.astimezone(timezone.utc).date()
    path=root/str(day.year)/f"{day.isoformat()}.json"
    if path.exists():
        # Immutable record of the first published daily snapshot.
        return path
    path.parent.mkdir(parents=True,exist_ok=True)
    # Exclusive creation prevents accidental rewrites of an existing snapshot.
    with path.open("x",encoding="utf-8") as file:
        json.dump(payload,file,ensure_ascii=False,separators=(",",":"))
        file.write("\n")
    return path

def archive_slot(payload:dict, root:Path=ARCHIVE)->Path:
    """Immutable observed snapshot for each real six-hour scan slot.

    Slot evidence is separate from the legacy first-snapshot daily archive;
    it must not be merged into a fabricated current ranked signal feed.
    """
    if payload.get("schema")!="vestra_prebreakout_v1" or not isinstance(payload.get("signals"),list):
        raise ValueError("invalid scanner payload")
    when=datetime.fromisoformat(str(payload["generated_at"]).replace("Z","+00:00"))
    if when.tzinfo is None:raise ValueError("generated_at must include timezone")
    utc=when.astimezone(timezone.utc)
    slot=payload.get("scan_slot_utc")
    if type(slot) is not int or slot!=utc.hour//6:
        raise ValueError("invalid or mismatched scan slot")
    day=utc.date()
    path=root/str(day.year)/"slots"/f"{day.isoformat()}-slot{slot}.json"
    if path.exists():return path
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("x",encoding="utf-8") as file:
        json.dump(payload,file,ensure_ascii=False,separators=(",",":"))
        file.write("\n")
    return path

if __name__=="__main__":
    payload=json.loads(CURRENT.read_text(encoding="utf-8"))
    print(archive(payload))
    print(archive_slot(payload))
