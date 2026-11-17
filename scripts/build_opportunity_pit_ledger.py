#!/usr/bin/env python3
"""Immutable daily research observations for all three opportunity engines.

Captures what was known, including rejected and control assets. No historical
signal is reconstructed from today's fundamentals and no outcome is inferred.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/"data"/"opportunity-pit-history"


def _timestamp(raw):
    stamp=datetime.fromisoformat(str(raw).replace("Z","+00:00"))
    if stamp.tzinfo is None:raise ValueError("source timestamp must be timezone-aware")
    return stamp.astimezone(timezone.utc)


def _sample(ticker, day, cap):
    value=int(hashlib.sha256(f"{day}:{ticker}".encode()).hexdigest()[:12],16)
    return value%1000<cap


def build(index, prebreakout, smallcap, captured_at):
    now=_timestamp(captured_at)
    sources=(index,prebreakout,smallcap)
    stamps=[_timestamp(s["generated_at"]) for s in sources]
    if any(stamp>now for stamp in stamps):
        raise ValueError("source published after capture time")
    if prebreakout.get("schema")!="vestra_prebreakout_v1":
        raise ValueError("unexpected prebreakout schema")
    if smallcap.get("schema")!="vestra_breakout_lab_smallcap_ohlcv_research_v1":
        raise ValueError("unexpected smallcap schema")
    day=now.date().isoformat()
    stocks=index.get("stocks")
    if not isinstance(stocks,list):raise ValueError("missing market index")
    low52=[]
    included={"all_near_or_risk":0,"sampled_controls":0}
    for row in stocks:
        ticker=str(row.get("ticker") or "").strip().upper()
        if not ticker or str(row.get("quote_type") or "").upper()!="EQUITY":continue
        status=row.get("low52_status")
        if status in ("opportunity","watch","uncertain","value_trap_risk","structural_risk"):
            included["all_near_or_risk"]+=1
        elif status in ("not_near_low","insufficient") and _sample(ticker,day,100):
            included["sampled_controls"]+=1
        else:continue
        low52.append({"ticker":ticker,"status":status,
            "current_price":row.get("current_price"),
            "current_price_timestamp_verified":False,
            "observed_low_session":row.get("low52_observed_last_session"),
            "observed_low_basis":row.get("low52_price_basis"),
            "distance_from_low_pct":row.get("low52_above_low_pct"),
            "low52_score":row.get("low52_score"),
            "risk_gate":row.get("risk_gate"),
            "evidence_coverage_pct":row.get("data_coverage_pct")})
    pre=prebreakout.get("research_observations") or {}
    pre_rows=pre.get("rows") if isinstance(pre,dict) else None
    if pre_rows is None:pre_rows=[]  # Old feeds cannot be retroactively completed.
    if not isinstance(pre_rows,list):raise ValueError("invalid prebreakout research census")
    small_rows=[]
    for row in smallcap.get("observations",[]):
        if not isinstance(row,dict) or not row.get("ticker"):continue
        small_rows.append({"ticker":row["ticker"],"status":row.get("status"),
            "last_session":row.get("last_session"),
            "adjusted_close":row.get("last_adjusted_close"),
            "first_rejection":row.get("technical_first_rejection"),
            "geometry":row.get("technical_geometry_shadow"),
            "average_dollar_volume_20_usd":row.get("average_dollar_volume_20_usd"),
            "no_future_outcome_at_capture":True})
    return {"schema":"vestra_three_engine_pit_daily_v1",
        "captured_at":now.isoformat(),"historical_capture_only":True,
        "not_backtest_or_predictive_validation":True,
        "sources":{"market_index":stamps[0].isoformat(),
                   "prebreakout":stamps[1].isoformat(),
                   "smallcap":stamps[2].isoformat()},
        "low52":{"selection":"all_classified_near_or_risk_plus_hash_sampled_controls_10pct",
                 "control_sample_key":"utc_capture_day_and_ticker_sha256",
                 "counts":included,"rows":sorted(low52,key=lambda r:r["ticker"])},
        "prebreakout":{"current_slot_research_census_available":bool(pre_rows),
                       "rows":pre_rows},
        "smallcap":{"rows":sorted(small_rows,key=lambda r:r["ticker"])}}


def archive(payload, root=ARCHIVE):
    now=_timestamp(payload["captured_at"])
    path=Path(root)/str(now.year)/(now.date().isoformat()+".json")
    if path.exists():return path
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("x",encoding="utf-8") as fh:
        json.dump(payload,fh,ensure_ascii=False,separators=(",",":"),allow_nan=False)
        fh.write("\n")
    return path


if __name__=="__main__":
    paths=(ROOT/"data/stocks-index.json",ROOT/"data/prebreakout-signals.json",
           ROOT/"data/breakout-lab-smallcap-ohlcv-research.json")
    sources=[json.loads(p.read_text(encoding="utf-8")) for p in paths]
    result=build(*sources,datetime.now(timezone.utc).isoformat())
    path=archive(result)
    print(json.dumps({"path":str(path),"prebreakout_rows":len(result["prebreakout"]["rows"]),
        "smallcap_rows":len(result["smallcap"]["rows"]),
        "low52_rows":len(result["low52"]["rows"])}))
