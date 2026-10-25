#!/usr/bin/env python3
"""Chronology of *observed* scanner stage changes from immutable slot archives.

Absence from a bounded rotating scan does not imply invalidation. Never fabricate
a stage, an entry signal, or a previously unobserved scan.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/"data"/"prebreakout-history"
OUTPUT=ROOT/"data"/"prebreakout-transitions.json"
STAGES={"compressão","pré-breakout","confirmado"}

def build(archive:Path=ARCHIVE)->dict:
    scans=[]
    for path in archive.glob("*/slots/*-slot*.json"):
        try:
            feed=json.loads(path.read_text(encoding="utf-8"))
            time=datetime.fromisoformat(str(feed["generated_at"]).replace("Z","+00:00"))
            if time.tzinfo is None or feed.get("schema")!="vestra_prebreakout_v1":continue
            time=time.astimezone(timezone.utc)
            slot=feed.get("scan_slot_utc")
            if type(slot) is not int or slot!=time.hour//6 or path.name!=f"{time.date().isoformat()}-slot{slot}.json":continue
            if not isinstance(feed.get("signals"),list):continue
            scans.append((time,path.name,feed))
        except (OSError,KeyError,TypeError,ValueError,AttributeError):
            continue
    scans.sort(key=lambda s:(s[0],s[1]))
    previous={};events=[]
    for stamp,filename,feed in scans:
        seen=set()
        for item in feed["signals"]:
            if not isinstance(item,dict):continue
            verified=item.get("scanner_verified_at")
            if verified is not None:
                try:
                    actual=datetime.fromisoformat(str(verified).replace("Z","+00:00"))
                    if actual.tzinfo is None or actual.astimezone(timezone.utc)!=stamp:continue
                except (ValueError,TypeError,AttributeError):continue
            ticker=str(item.get("ticker") or "").strip().upper()
            stage=item.get("stage")
            if not ticker or stage not in STAGES or item.get("source")!="yahoo:daily_ohlcv" or ticker in seen:continue
            seen.add(ticker)
            try:score=float(item["score"])
            except (KeyError,ValueError,TypeError):continue
            if not 0<=score<=100:continue
            prior=previous.get(ticker)
            if prior is None or prior["stage"]!=stage:
                events.append({"ticker":ticker,"event":"first_observed" if prior is None else "stage_changed",
                    "from_stage":None if prior is None else prior["stage"],"to_stage":stage,
                    "observed_at":stamp.isoformat(),"scan_slot_utc":feed["scan_slot_utc"],
                    "signal_date":item.get("date"),"score":score})
            previous[ticker]={"stage":stage,"last_observed_at":stamp.isoformat()}
    return {"schema":"vestra_prebreakout_transitions_v1","historical_only":True,
        "scans_considered":len(scans),"events":events,
        "last_observed":dict(sorted(previous.items()))}

if __name__=="__main__":
    OUTPUT.write_text(json.dumps(build(),ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
