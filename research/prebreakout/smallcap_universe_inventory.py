#!/usr/bin/env python3
"""Breakout Lab: independent small-cap universe inventory (research only).

Does not modify the live scanner's liquidity gate, ranking, or price engine.
A company belonging to this inventory is NOT a verified breakout candidate.
"""
from __future__ import annotations
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MIN_CAP=100_000_000
MAX_CAP=2_000_000_000
EXCLUDED={"ETF","FUND","MUTUALFUND","CRYPTO"}

def inventory(stocks: list[dict]) -> dict:
    universe={}
    rejected={"missing_or_bad_cap":0,"below_100m":0,"above_2b":0,"non_equity":0,"invalid_ticker":0}
    for row in stocks:
        if not isinstance(row,dict):
            rejected["invalid_ticker"]+=1
            continue
        ticker=str(row.get("ticker") or "").strip().upper()
        if not ticker:
            rejected["invalid_ticker"]+=1
            continue
        if str(row.get("quote_type") or "").upper() in EXCLUDED:
            rejected["non_equity"]+=1
            continue
        cap=row.get("market_cap")
        if type(cap) not in (int,float) or not math.isfinite(cap) or cap<=0:
            rejected["missing_or_bad_cap"]+=1
            continue
        if cap<MIN_CAP:
            rejected["below_100m"]+=1
            continue
        if cap>MAX_CAP:
            rejected["above_2b"]+=1
            continue
        universe[ticker]=max(float(cap),universe.get(ticker,0))
    micro=sum(cap<500_000_000 for cap in universe.values())
    overlap=len(universe)-micro
    return {"schema":"vestra_breakout_lab_smallcap_inventory_v1",
            "status":"universe_inventory_only_not_ohlcv_verified",
            "range_usd":[MIN_CAP,MAX_CAP],
            "distinct_tickers":len(universe),
            "under_live_scanner_cap_floor":micro,
            "overlap_with_live_cap_universe":overlap,
            "excluded_input_rows":rejected,
            "tickers":sorted(universe),
            "no_predictive_edge_claim":True}

def main() -> None:
    stocks=json.loads((ROOT/"data/stocks-index.json").read_text(encoding="utf-8")).get("stocks",[])
    result=inventory(stocks)
    print(json.dumps(result,ensure_ascii=False,separators=(",",":")))

if __name__=="__main__":
    main()
