#!/usr/bin/env python3
"""Fail closed before publishing a scanner snapshot with inconsistent evidence."""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def verify(root:Path=ROOT):
    data=root/"data"
    feed=json.loads((data/"prebreakout-signals.json").read_text(encoding="utf-8"))
    index=json.loads((data/"prebreakout-observations.json").read_text(encoding="utf-8"))
    stamp=datetime.fromisoformat(str(feed["generated_at"]).replace("Z","+00:00"))
    if stamp.tzinfo is None:raise ValueError("publisher must use timezone-aware timestamp")
    utc=stamp.astimezone(timezone.utc)
    slot=feed.get("scan_slot_utc")
    if type(slot) is not int or slot!=utc.hour//6:raise ValueError("incorrect scanner slot")
    if feed.get("schema")!="vestra_prebreakout_v1" or not isinstance(feed.get("signals"),list):
        raise ValueError("invalid current publisher")
    file=data/"prebreakout-history"/str(utc.year)/"slots"/f"{utc.date().isoformat()}-slot{slot}.json"
    archived=json.loads(file.read_text(encoding="utf-8"))
    if archived!=feed:raise ValueError("published slot differs from feed")
    if index.get("schema")!="vestra_prebreakout_observations_v1" or index.get("historical_only") is not True:
        raise ValueError("observations must remain historical only")
    if not isinstance(index.get("observations"),list) or index.get("slots_considered",0)<1:
        raise ValueError("missing archived observation evidence")
    observations={row.get("ticker"):row for row in index["observations"]}
    for row in feed["signals"]:
        candidate=observations.get(row["ticker"])
        if candidate is None:raise ValueError("latest observed ticker missing from historical index")
        verified=row.get("scanner_verified_at")
        if verified is not None:
            observed=datetime.fromisoformat(str(verified).replace("Z","+00:00"))
            if observed.tzinfo is None or observed.astimezone(timezone.utc)>utc:
                raise ValueError("invalid signal verification time")
            expected=observed.astimezone(timezone.utc).isoformat()
        else:
            expected=utc.isoformat()  # Legacy archives lacked per-row provenance.
        if candidate.get("observed_at")!=expected:raise ValueError("observation timestamp mismatch")
        if candidate.get("stage")!=row["stage"] or candidate.get("signal_date")!=row["date"]:
            raise ValueError("latest observation stage/date mismatch")
        if candidate.get("current") is not False:raise ValueError("history promoted to current")
    return {"verified_slot":slot,"observations":len(index["observations"]),"new_signals":len(feed["signals"])}

if __name__=="__main__":
    print(json.dumps(verify()))
