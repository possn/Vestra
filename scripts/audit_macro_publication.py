#!/usr/bin/env python3
"""Audit published macro calendar freshness without fabricating official events."""
from __future__ import annotations
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

SOURCES=("fed","bls","bea","ecb","census")
MAX_AGE=timedelta(hours=36)

def audit(payload:dict, now:datetime)->dict:
    if now.tzinfo is None:raise ValueError("timezone-aware now required")
    if not isinstance(payload,dict) or payload.get("schema_version")!=2:raise ValueError("invalid macro calendar")
    try: stamp=datetime.fromisoformat(str(payload["generated_at"]).replace("Z","+00:00"))
    except (ValueError,TypeError,KeyError) as exc:raise ValueError("missing publication time") from exc
    if stamp.tzinfo is None:raise ValueError("publication timezone missing")
    age=now.astimezone(timezone.utc)-stamp.astimezone(timezone.utc)
    if age<timedelta(minutes=-5):raise ValueError("future-dated publication")
    status=payload.get("source_status")
    if not isinstance(status,dict):raise ValueError("source statuses missing")
    sources={}
    for source in SOURCES:
        state=status.get(source)
        if not isinstance(state,dict) or state.get("state") not in ("fresh","fallback"):
            sources[source]="unknown"
        else:sources[source]=state["state"]
    events=payload.get("events")
    if not isinstance(events,list):raise ValueError("events missing")
    return {"schema":"vestra_macro_calendar_publication_audit_v1",
            "generated_at":stamp.isoformat(),"age_hours":round(age.total_seconds()/3600,2),
            "publication_fresh":age<=MAX_AGE,
            "source_status":sources,
            "missing_sources":[s for s in SOURCES if sources[s]=="unknown"],
            "critical_events_present":sum(e.get("importance")=="critical" for e in events if isinstance(e,dict)),
            "refresh_needed":age>MAX_AGE or any(sources[s]=="unknown" for s in SOURCES),
            "meaning":"timestamp measures last successful publication, not independent correctness of each official release"}

def main()->int:
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--file",type=Path,default=Path("data/macro-events.json"))
    p.add_argument("--check",action="store_true")
    args=p.parse_args()
    report=audit(json.loads(args.file.read_text(encoding="utf-8")),datetime.now(timezone.utc))
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 1 if args.check and report["refresh_needed"] else 0

if __name__=="__main__":raise SystemExit(main())
