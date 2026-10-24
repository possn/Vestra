#!/usr/bin/env python3
"""Allow a live retry only for a due scanner slot without a published immutable snapshot."""
import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def should_scan(now:datetime, archive:Path)->bool:
    if now.tzinfo is None:
        raise ValueError("UTC-aware clock required")
    now=now.astimezone(timezone.utc)
    # Friday US cash session closes after the 20:10 UTC scanner slot.
    # Saturday 02:10 UTC is the first guaranteed weekly-complete snapshot.
    if now.weekday()==6 or (now.weekday()==5 and now.hour>=6):
        return False
    slot=now.hour//6
    scheduled_hour=(2,8,14,20)[slot]
    # Never manufacture an earlier slot's snapshot or run ahead of its scheduled time.
    if (now.hour,now.minute)<(scheduled_hour,10):
        return False
    file=archive/str(now.year)/"slots"/f"{now.date().isoformat()}-slot{slot}.json"
    # Existing slot is immutable, even if damaged: signal operational alert, not overwrite.
    return not file.exists()

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--archive",type=Path,default=ROOT/"data/prebreakout-history")
    args=parser.parse_args()
    now=datetime.now(timezone.utc)
    enabled=should_scan(now,args.archive)
    output=os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output,"a",encoding="utf-8") as f:
            f.write(f"scan={'true' if enabled else 'false'}\\n".replace("\\n","\n"))
    print(json.dumps({"utc_now":now.isoformat(),"slot":now.hour//6,"scan":enabled}))
