#!/usr/bin/env python3
"""Build a historical watchlist from real immutable scan-slot publications only.

Historical observations are NOT current trading signals and cannot modify the
canonical data/prebreakout-signals.json feed.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/"data/prebreakout-history"
OUTPUT=ROOT/"data/prebreakout-observations.json"
STAGES={"confirmado","pré-breakout","compressão"}

def build(root:Path=ARCHIVE, now:datetime|None=None, days:int=7)->dict:
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None:raise ValueError("timezone required")
    now=now.astimezone(timezone.utc)
    observations={}
    checked=0
    for path in sorted(root.glob("*/slots/*-slot*.json")):
        try:
            payload=json.loads(path.read_text(encoding="utf-8"))
            ts=datetime.fromisoformat(str(payload["generated_at"]).replace("Z","+00:00"))
            if ts.tzinfo is None:continue
            ts=ts.astimezone(timezone.utc)
            delta=(now-ts).total_seconds()/86400
            if not 0<=delta<=days or payload.get("schema")!="vestra_prebreakout_v1":continue
            slot=payload.get("scan_slot_utc")
            if type(slot) is not int or slot!=ts.hour//6 or not isinstance(payload.get("signals"),list):continue
            if path.name!=f"{ts.date().isoformat()}-slot{slot}.json":continue
            checked+=1
            for row in payload["signals"]:
                if not isinstance(row,dict):continue
                # A carried signal was not observed again at this scan slot.
                verified=row.get("scanner_verified_at")
                if verified is not None:
                    try:
                        actual=datetime.fromisoformat(str(verified).replace("Z","+00:00"))
                        if actual.tzinfo is None or actual.astimezone(timezone.utc)!=ts:continue
                    except (ValueError,TypeError,AttributeError):continue
                ticker=str(row.get("ticker") or "").strip().upper()
                if not ticker or row.get("stage") not in STAGES or row.get("source")!="yahoo:daily_ohlcv":continue
                try:
                    score=float(row["score"])
                except (ValueError,TypeError,KeyError):continue
                if not 0<=score<=100:continue
                record={"ticker":ticker,"stage":row["stage"],"score":score,
                        "signal_date":row.get("date"),"observed_at":ts.isoformat(),
                        "scan_slot_utc":slot,"current":False}
                if ticker not in observations or record["observed_at"]>observations[ticker]["observed_at"]:
                    observations[ticker]=record
        except (OSError,ValueError,TypeError,KeyError,json.JSONDecodeError):
            continue
    return {"schema":"vestra_prebreakout_observations_v1","generated_at":now.isoformat(),
            "historical_only":True,"slots_considered":checked,
            "observations":sorted(observations.values(),key=lambda r:(-r["score"],r["ticker"]))[:100]}

if __name__=="__main__":
    OUTPUT.write_text(json.dumps(build(),ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
