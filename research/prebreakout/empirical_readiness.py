#!/usr/bin/env python3
"""Fail-closed readiness audit of existing prospective pre-breakout evidence.

Reads the published cohort artifact only; never manufactures outcome labels,
imputes OHLCV, or treats a missing measurement as a failed trade.
"""
from __future__ import annotations
import json
from pathlib import Path

HORIZONS=("5","10","20")
REASONS=("price_basis_unverified","missing_ohlcv","pending")

def audit(data:dict)->dict:
    if not isinstance(data,dict) or data.get("schema")!="vestra_prebreakout_forward_cohorts_v1":
        raise ValueError("invalid forward cohort artifact")
    root=data.get("breakout_event_evidence")
    if not isinstance(root,dict) or not isinstance(root.get("coverage_by_horizon"),dict):
        raise ValueError("missing breakout evidence")
    results={}
    for h in HORIZONS:
        row=root["coverage_by_horizon"].get(h)
        if not isinstance(row,dict):
            raise ValueError("missing horizon "+h)
        cohorts,evaluable=row.get("cohorts"),row.get("evaluable")
        if type(cohorts) is not int or type(evaluable) is not int or not 0<=evaluable<=cohorts:
            raise ValueError("invalid horizon counts")
        statuses=row.get("by_status")
        if not isinstance(statuses,dict) or any(type(v) is not int or v<0 for v in statuses.values()):
            raise ValueError("invalid status counts")
        if sum(statuses.values())+evaluable!=cohorts:
            raise ValueError("unreconciled evidence denominators")
        if evaluable==0 and row.get("breakout_rate") is not None:
            raise ValueError("fabricated breakout rate without observations")
        blockers={key:statuses.get(key,0) for key in REASONS}
        other={k:v for k,v in statuses.items() if k not in REASONS}
        results[h]={"cohorts":cohorts,"evaluable":evaluable,
                    "coverage_pct":round(evaluable*100/cohorts,2) if cohorts else None,
                    "blockers":blockers,"other_unverified":other,
                    "ready_for_discrimination":False,
                    "reason":"no_verified_outcomes" if evaluable==0 else "requires_episode_level_pit_feature_join_and_oos_validation"}
    return {"schema":"vestra_prebreakout_empirical_readiness_v1",
            "source":"data/prebreakout-forward-evidence.json",
            "predictive_edge_established":False,"filter_promotion_approved":False,
            "horizons":results}

def markdown(report:dict)->str:
    lines=["# Pre-breakout — evidence readiness audit","","Research only. No production signal, score or threshold changes.","",
           "| Sessions | Cohorts | Evaluable | Unverified basis | Missing OHLCV | Pending |",
           "|---|---:|---:|---:|---:|---:|"]
    for h,r in report["horizons"].items():
        b=r["blockers"]
        lines.append(f'| {h} | {r["cohorts"]} | {r["evaluable"]} | {b["price_basis_unverified"]} | {b["missing_ohlcv"]} | {b["pending"]} |')
    lines += ["","**Conclusion:** No claim of breakout success rate, calibrated probability or discrimination edge is supported by zero verified outcomes.",
              "Missing, unverifiable and pending are NOT failed breakouts.",
              "The pre-base impulse features introduced in #1608 and the cohort comparison in #1609 require independently verified point-in-time inputs and matured outcomes before any deployment decision.",
              ""]
    return "\n".join(lines)

if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--source",type=Path,default=Path("data/prebreakout-forward-evidence.json"))
    parser.add_argument("--format",choices=("json","markdown"),default="markdown")
    args=parser.parse_args()
    result=audit(json.loads(args.source.read_text(encoding="utf-8")))
    print(markdown(result) if args.format=="markdown" else json.dumps(result,ensure_ascii=False,indent=2))
