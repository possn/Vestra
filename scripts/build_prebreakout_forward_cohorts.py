#!/usr/bin/env python3
"""Forward cohorts based only on immutable, originally published scanner slots.

A ticker's first publication per stage defines one research cohort. Repeated
scans of the same stage never inflate sample size. No backfilled signals.
Price histories are supplied independently; missing prices remain missing.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from prebreakout_forward_evaluation import evaluate_archived
from prebreakout_stage_evidence import report
from prebreakout_forward_events import breakout_event

STAGES={"compressão","pré-breakout","confirmado"}

def base_maturity(case:dict)->str:
    """Published age in calendar days; never mislabel elapsed days as market sessions."""
    anchor=case.get("base_start_date")
    if not anchor:
        return "unverified"
    days=(datetime.fromisoformat(case["signal_date"]).date()-
          datetime.fromisoformat(anchor).date()).days
    if days<0:
        return "unverified"
    if days<28:
        return "young_under_28d"
    if days<=84:
        return "developing_28_to_84d"
    return "extended_over_84d"


def maturity_event_evidence(events:list[dict],cases:list[dict])->dict:
    """Transparent sample counts, no fitted probabilities or invented labels."""
    groups={}
    for case in cases:
        group=base_maturity(case)
        groups.setdefault(group,{"cohorts":0,"by_horizon":{str(h):{"confirmed":0,"not_confirmed":0,"pending_or_unverified":0} for h in (5,10,20)}})
        groups[group]["cohorts"]+=1
    for event in events:
        group=event["base_maturity"]
        bucket=groups[group]["by_horizon"][str(event["horizon_sessions"])]
        status=event["status"]
        if status in ("confirmed","not_confirmed"):
            bucket[status]+=1
        else:
            bucket["pending_or_unverified"]+=1
    for group in groups.values():
        for bucket in group["by_horizon"].values():
            bucket["evaluable"]=bucket["confirmed"]+bucket["not_confirmed"]
            bucket["breakout_probability"]=None
    return {"age_unit":"calendar_days","historical_only":True,
            "probability_calibrated":False,"groups":groups}


def cohorts(archive:Path)->list[dict]:
    eligible=[]
    for path in archive.glob("*/slots/*-slot*.json"):
        try:
            data=json.loads(path.read_text(encoding="utf-8"))
            stamp=datetime.fromisoformat(str(data["generated_at"]).replace("Z","+00:00"))
            if stamp.tzinfo is None or data.get("schema")!="vestra_prebreakout_v1":continue
            stamp=stamp.astimezone(timezone.utc)
            slot=data.get("scan_slot_utc")
            if type(slot) is not int or slot!=stamp.hour//6:continue
            if path.name!=f"{stamp.date().isoformat()}-slot{slot}.json":continue
            if not isinstance(data.get("signals"),list):continue
            eligible.append((stamp,path.name,data))
        except (OSError,KeyError,TypeError,ValueError):
            continue
    selected={}
    for stamp,name,data in sorted(eligible,key=lambda x:(x[0],x[1])):
        counts={}
        for row in data["signals"]:
            if not isinstance(row,dict):continue
            ticker=str(row.get("ticker") or "").strip().upper()
            if not ticker or row.get("stage") not in STAGES or row.get("source")!="yahoo:daily_ohlcv":continue
            counts[ticker]=counts.get(ticker,0)+1
        for row in data["signals"]:
            if not isinstance(row,dict):continue
            ticker=str(row.get("ticker") or "").strip().upper()
            stage=row.get("stage")
            if not ticker or counts.get(ticker)!=1 or stage not in STAGES or row.get("source")!="yahoo:daily_ohlcv":continue
            try:
                date=datetime.fromisoformat(str(row["date"])[:10]).date()
            except (ValueError,TypeError,KeyError):continue
            if date>stamp.date():continue
            # Point-in-time base identity: never combine two independently
            # published bases merely because the ticker/stage is the same.
            # Legacy publications lacking an explicit base start remain on
            # the old ticker/stage policy; do not retroactively invent bases.
            anchor=row.get("baseStartDate")
            if anchor is not None:
                try:
                    base_date=datetime.fromisoformat(str(anchor)).date()
                except (TypeError,ValueError):
                    continue
                if base_date>date or (date-base_date).days>365:
                    continue
                anchor=base_date.isoformat()
            key=(ticker,stage,anchor)
            if key not in selected:
                selected[key]={"ticker":ticker,"stage":stage,
                    "base_start_date":anchor,
                    "published_at":stamp.isoformat(),"signal_date":date.isoformat(),
                    "snapshot":data}
    return [selected[k] for k in sorted(selected,key=lambda key:(selected[key]["published_at"],key))]

def build(archive:Path,prices:dict,benchmark_bars:list[dict],event_prices:dict|None=None)->dict:
    cases=cohorts(archive)
    outcomes=[]
    for case in cases:
        bars=prices.get(case["ticker"])
        if not isinstance(bars,list) or not isinstance(benchmark_bars,list):
            outcome={"ticker":case["ticker"],"stage":case["stage"],"published_at":case["published_at"],
                     "signal_date":case["signal_date"],"entry":None,"results":{}}
        else:
            try:
                outcome=evaluate_archived(case["snapshot"],case["ticker"],bars,benchmark_bars)
            except (ValueError,TypeError,KeyError,ZeroDivisionError):
                outcome={"ticker":case["ticker"],"stage":case["stage"],"published_at":case["published_at"],
                         "signal_date":case["signal_date"],"entry":None,"results":{}}
        outcomes.append(outcome)
    events=[]
    for case in cases:
        rows=(event_prices or {}).get(case["ticker"])
        for horizon in (5,10,20):
            event={"ticker":case["ticker"],"stage":case["stage"],
                   "published_at":case["published_at"],"horizon_sessions":horizon,
                   "base_maturity":base_maturity(case)}
            if not isinstance(rows,list) or not rows:
                event.update({"status":"missing_ohlcv","observed_sessions":0,"event_date":None})
            else:
                try:
                    event.update(breakout_event(case["snapshot"],case["ticker"],rows,horizon))
                except (ValueError,KeyError,TypeError,OverflowError):
                    event.update({"status":"invalid_ohlcv","observed_sessions":0,"event_date":None})
            events.append(event)
    # Publish the denominator explicitly: pending/unverifiable cohorts are
    # never silently counted as breakouts that failed.
    event_coverage={}
    for horizon in (5,10,20):
        sample=[row for row in events if row["horizon_sessions"]==horizon]
        counts={}
        for row in sample:
            status=row["status"]
            counts[status]=counts.get(status,0)+1
        evaluated=counts.get("confirmed",0)+counts.get("not_confirmed",0)
        matured=sum(1 for row in sample if row.get("horizon_matured") is True)
        confirmed_early=sum(1 for row in sample if row["status"]=="confirmed" and row.get("horizon_matured") is False)
        # Durability is measured only where the post-confirmation horizon is complete.
        # A confirmed trigger is not automatically a durable success.
        durability={}
        for window in ("3","5","10"):
            observed=[row["durability"][window] for row in sample
                      if row["status"]=="confirmed" and
                      isinstance(row.get("durability"),dict) and
                      isinstance(row["durability"].get(window),dict) and
                      row["durability"][window].get("status")=="observed" and
                      type(row["durability"][window].get("held_pivot")) is bool]
            durability[window]={"observed":len(observed),
                "held_pivot":sum(row["held_pivot"] for row in observed),
                "lost_pivot":sum(not row["held_pivot"] for row in observed)}
        event_coverage[str(horizon)]={
            "cohorts":len(sample),"evaluable":evaluated,
            "matured_horizons":matured,"confirmed_before_maturity":confirmed_early,
            "post_confirmation_durability":durability,
            "coverage":round(evaluated/len(sample),4) if sample else None,
            "by_status":counts,"breakout_rate":None,
            "reason":"insufficient_or_unverified_forward_evidence"}
    return {"schema":"vestra_prebreakout_forward_cohorts_v1",
        "breakout_event_evidence":{"historical_only":True,"method":"published_pivot_future_ohlcv",
            "unvalidated_probability":True,"coverage_by_horizon":event_coverage,"events":events},
        "evaluation_method":"adjusted_daily_close_after_publication",
        "cohort_policy":"first_immutable_publication_per_ticker_stage_and_verified_base_start",
        "historical_only":True,"cohort_count":len(cases),
        "base_identity_coverage":{"anchored":sum(case["base_start_date"] is not None for case in cases),
                                  "legacy_unanchored":sum(case["base_start_date"] is None for case in cases)},
        "base_maturity_evidence":maturity_event_evidence(events,cases),
        "stage_evidence":report(outcomes),"outcomes":outcomes}

if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--archive",type=Path,default=Path(__file__).resolve().parents[1]/"data/prebreakout-history")
    parser.add_argument("--prices",type=Path,required=True,help="JSON map ticker -> adjusted OHLCV bars, plus SPY benchmark")
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    prices=json.loads(args.prices.read_text(encoding="utf-8"))
    if not isinstance(prices,dict) or not isinstance(prices.get("SPY"),list):
        raise ValueError("require independent SPY adjusted daily benchmark")
    result=build(args.archive,prices,prices["SPY"])
    args.output.write_text(json.dumps(result,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
