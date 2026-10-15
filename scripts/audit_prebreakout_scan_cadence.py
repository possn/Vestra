#!/usr/bin/env python3
"""Report missing scheduled scanner publications; diagnostic only, never fabricate a scan."""
import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SLOT_HOURS=(2,8,14,20)

def audit(archive:Path,now:datetime,grace_minutes:int=90,days:int=2):
    if now.tzinfo is None or grace_minutes<0 or days<1:raise ValueError("invalid audit clock/window")
    now=now.astimezone(timezone.utc)
    missing=[];present=[]
    for offset in range(days):
        day=(now-timedelta(days=offset)).date()
        if day.weekday()>=5:continue
        for hour in SLOT_HOURS:
            scheduled=datetime(day.year,day.month,day.day,hour,10,tzinfo=timezone.utc)
            if now<scheduled+timedelta(minutes=grace_minutes):continue
            slot=hour//6
            path=archive/str(day.year)/"slots"/f"{day.isoformat()}-slot{slot}.json"
            valid=False
            try:
                feed=json.loads(path.read_text(encoding="utf-8"))
                stamp=datetime.fromisoformat(str(feed["generated_at"]).replace("Z","+00:00"))
                valid=(stamp.tzinfo is not None and stamp.astimezone(timezone.utc).date()==day
                    and feed.get("scan_slot_utc")==slot and feed.get("schema")=="vestra_prebreakout_v1")
            except (OSError,ValueError,KeyError,TypeError):
                pass
            (present if valid else missing).append(day.isoformat()+f"-slot{slot}")
    return {"schema":"vestra_prebreakout_cadence_audit_v1","checked_after_grace_minutes":grace_minutes,
            "present":sorted(present),"missing_or_invalid":sorted(missing),
            "status":"attention" if missing else "ok"}

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--archive",type=Path,default=ROOT/"data/prebreakout-history")
    ap.add_argument("--days",type=int,default=2)
    ap.add_argument("--grace-minutes",type=int,default=90)
    args=ap.parse_args()
    result=audit(args.archive,datetime.now(timezone.utc),args.grace_minutes,args.days)
    print(json.dumps(result,ensure_ascii=False))
    if result["missing_or_invalid"]:
        print("::warning::Missing or invalid prebreakout scanner slots: "+", ".join(result["missing_or_invalid"]))
