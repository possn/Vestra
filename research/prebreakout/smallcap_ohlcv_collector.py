#!/usr/bin/env python3
"""Independent, bounded *observed* OHLCV collector for USD 100m–500m small caps.

Research output only. Never writes production signals or modifies quote engines.
Missing data and uncertain currencies are failures, not zeroes or signals.
"""
from __future__ import annotations
import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT=ROOT/"data"/"breakout-lab-smallcap-ohlcv-research.json"
MAX_PER_RUN=30
MIN_BARS=220

def cohort(rows):
    found={}
    for row in rows:
        if not isinstance(row,dict):continue
        symbol=str(row.get("ticker") or "").strip().upper()
        cap=row.get("market_cap")
        kind=str(row.get("quote_type") or "").upper()
        if (not symbol or kind in {"ETF","FUND","MUTUALFUND","CRYPTO"}
            or type(cap) not in (int,float) or not math.isfinite(cap)
            or not 100_000_000<=cap<500_000_000):continue
        found[symbol]=max(float(cap),found.get(symbol,0))
    return sorted(found)

def inspect(ticker,frame,currency,checked_at):
    if currency!="USD":
        return {"ticker":ticker,"status":"currency_not_verified_usd","currency":currency}
    if frame is None or getattr(frame,"empty",True):
        return {"ticker":ticker,"status":"no_ohlcv"}
    clean=[]
    try:
        for timestamp,row in frame.iterrows():
            day=timestamp.date().isoformat()
            values=[float(row[k]) for k in ("Open","High","Low","Close","Volume")]
            o,h,l,c,v=values
            if not all(map(math.isfinite,values)) or not (0<l<=min(o,c)<=max(o,c)<=h and v>0):
                return {"ticker":ticker,"status":"invalid_ohlcv"}
            if clean and day<=clean[-1][0]:
                return {"ticker":ticker,"status":"unordered_or_duplicate_sessions"}
            clean.append((day,c,v))
    except (KeyError,TypeError,ValueError,OverflowError,AttributeError):
        return {"ticker":ticker,"status":"invalid_ohlcv"}
    if len(clean)<MIN_BARS:return {"ticker":ticker,"status":"insufficient_ohlcv","bars":len(clean)}
    # Actual USD turnover, not volume in shares or a forecast.
    turnover=sum(c*v for _,c,v in clean[-20:])/20
    last=clean[-1][0]
    age=(checked_at.date()-datetime.fromisoformat(last).date()).days
    if not 0<=age<=7:return {"ticker":ticker,"status":"stale_ohlcv","last_session":last}
    return {"ticker":ticker,"status":"evaluable_ohlcv","bars":len(clean),
            "first_session":clean[0][0],"last_session":last,
            "average_dollar_volume_20_usd":round(turnover,2),
            "liquidity_5m_usd_verified":turnover>=5_000_000,
            "spread_verified":False,"gap_risk_not_assessed":True,
            "currency":"USD","price_basis":"yfinance_auto_adjusted",
            "ohlcv_observed_at":checked_at.isoformat()}

def collect(rows,provider,slot=0,budget=20,checked_at=None):
    if type(slot)!=int or slot<0 or type(budget)!=int or not 1<=budget<=MAX_PER_RUN:
        raise ValueError("slot must be >=0 and budget between 1 and 30")
    checked_at=checked_at or datetime.now(timezone.utc)
    if checked_at.tzinfo is None:raise ValueError("checked_at must be timezone-aware")
    names=cohort(rows)
    start=(slot*budget)%len(names) if names else 0
    selected=(names[start:]+names[:start])[:min(budget,len(names))] if names else []
    observed=[]
    for ticker in selected:
        try:
            item=provider.Ticker(ticker)
            currency=item.fast_info.get("currency")
            if currency!="USD":
                observed.append(inspect(ticker,None,currency,checked_at));continue
            frame=provider.download(ticker,period="18mo",interval="1d",auto_adjust=True,
                                    threads=False,progress=False,timeout=20)
            observed.append(inspect(ticker,frame,currency,checked_at))
        except Exception as exc:
            observed.append({"ticker":ticker,"status":"provider_error",
                             "error_type":type(exc).__name__})
    evaluable=sum(x["status"]=="evaluable_ohlcv" for x in observed)
    return {"schema":"vestra_breakout_lab_smallcap_ohlcv_research_v1",
            "status":"observed_research_only_not_breakout_signals",
            "generated_at":checked_at.isoformat(),"source":"yfinance",
            "universe_100m_500m_count":len(names),"slot":slot,"budget":budget,
            "provider_tickers_attempted":len(observed),
            "evaluable_ohlcv":evaluable,"observed_incomplete":len(observed)-evaluable,
            "not_observed":len(names)-len(observed),
            "universe_coverage_pct":round(100*evaluable/len(names),2) if names else None,
            "point_in_time_caveat":"market_caps_from_current_index_not_historical_asof_snapshots",
            "not_breakout_candidates":True,"no_success_probability":True,
            "observations":observed}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--slot",type=int,default=0)
    parser.add_argument("--budget",type=int,default=20)
    parser.add_argument("--output",type=Path,default=DEFAULT_OUTPUT)
    args=parser.parse_args()
    import yfinance as yf
    rows=json.loads((ROOT/"data/stocks-index.json").read_text()).get("stocks",[])
    result=collect(rows,yf,args.slot,args.budget)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k!="observations"}))

if __name__=="__main__":main()
