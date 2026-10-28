#!/usr/bin/env python3
"""Fail closed before publishing a scanner snapshot with inconsistent evidence."""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def assess_freshness(feed:dict, now:datetime, max_age_hours:float=8)->dict:
    """Read-only operational check; never infer full coverage from slot capacity."""
    if not isinstance(feed,dict) or feed.get("schema")!="vestra_prebreakout_v1":
        return {"status":"invalid","reason":"invalid_schema"}
    try:
        generated=datetime.fromisoformat(str(feed["generated_at"]).replace("Z","+00:00"))
        if generated.tzinfo is None or now.tzinfo is None:
            return {"status":"invalid","reason":"naive_timestamp"}
        age=(now-generated).total_seconds()/3600
        if not 0<=age<=max_age_hours:
            return {"status":"stale","age_hours":round(age,2)}
        slot=feed["scan_slot_telemetry"]
        audit=feed["scan_quality_audit"]
        coverage=feed["coverage_audit_24h"]
        capacity=feed["daily_capacity_ceiling"]
        expected=min(1200,feed["eligible_universe"])
        if (not isinstance(slot,dict) or not isinstance(audit,dict) or
            not isinstance(capacity,dict) or
            capacity.get("max_distinct_daily")!=expected or
            slot.get("rows_attempted")!=feed["attempted"] or
            audit.get("observed_24h_coverage_pct")!=coverage["coverage_pct"]):
            return {"status":"invalid","reason":"inconsistent_new_telemetry"}
    except (KeyError,TypeError,ValueError,AttributeError):
        return {"status":"invalid","reason":"missing_new_telemetry"}
    return {"status":"healthy","age_hours":round(age,2),
            "observed_24h_coverage_pct":coverage["coverage_pct"]}


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
