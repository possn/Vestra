#!/usr/bin/env python3
"""Independent, bounded *observed* OHLCV collector for USD 100m–500m small caps.

Research output only. Never writes production signals or modifies quote engines.
Missing data and uncertain currencies are failures, not zeroes or signals.
"""
from __future__ import annotations
import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
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
    full_bars=[]
    try:
        for timestamp,row in frame.iterrows():
            day=timestamp.date().isoformat()
            # A bar stamped today may reflect an unfinished trading session.
            # Exclude it conservatively instead of treating partial volume as final.
            if day == checked_at.date().isoformat():
                continue
            values=[float(row[k]) for k in ("Open","High","Low","Close","Volume")]
            o,h,l,c,v=values
            if not all(map(math.isfinite,values)) or not (0<l<=min(o,c)<=max(o,c)<=h and v>0):
                return {"ticker":ticker,"status":"invalid_ohlcv"}
            if clean and day<=clean[-1][0]:
                return {"ticker":ticker,"status":"unordered_or_duplicate_sessions"}
            clean.append((day,c,v))
            full_bars.append({'date':day,'open':o,'high':h,'low':l,'close':c,'volume':v})
    except (KeyError,TypeError,ValueError,OverflowError,AttributeError):
        return {"ticker":ticker,"status":"invalid_ohlcv"}
    if len(clean)<MIN_BARS:return {"ticker":ticker,"status":"insufficient_ohlcv","bars":len(clean)}
    # Actual USD turnover, not volume in shares or a forecast.
    turnover=sum(c*v for _,c,v in clean[-20:])/20
    last=clean[-1][0]
    age=(checked_at.date()-datetime.fromisoformat(last).date()).days
    if not 0<=age<=7:return {"ticker":ticker,"status":"stale_ohlcv","last_session":last}
    # Reuse the already-audited VCP/pre-breakout technical engine, not the
    # ordinary Discovery score or the inventory's market capitalization.
    from scripts.refresh_prebreakout_scanner import scan_bars
    setup=None
    if turnover>=1_000_000:
        setup=scan_bars(ticker,full_bars,checked_at.date(),
                        strict_quality=True,liquidity_floor=1_000_000)
    if setup:
        setup={**setup,"source":"yahoo:smallcap_daily_ohlcv",
               "currencyVerified":"USD","spreadVerified":False,
               "gapRisk":"not_verified","earningsRiskGate":"unknown",
               "observedAt":checked_at.isoformat()}
    return {"ticker":ticker,"status":"evaluable_ohlcv","bars":len(clean),
            "verified_prebreakout_setup":setup,
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
    cap_by_ticker={str(row.get("ticker") or "").strip().upper():row.get("market_cap")
                   for row in rows if isinstance(row,dict)}
    for ticker in selected:
        try:
            item=provider.Ticker(ticker)
            currency=item.fast_info.get("currency")
            if currency!="USD":
                observed.append(inspect(ticker,None,currency,checked_at));continue
            frame=provider.download(ticker,period="18mo",interval="1d",auto_adjust=True,
                                    threads=False,progress=False,timeout=20,multi_level_index=False)
            result=inspect(ticker,frame,currency,checked_at)
            if result.get("verified_prebreakout_setup"):
                result["verified_prebreakout_setup"]["marketCapUSD"]=cap_by_ticker[ticker]
            observed.append(result)
        except Exception as exc:
            observed.append({"ticker":ticker,"status":"provider_error",
                             "error_type":type(exc).__name__})
    evaluable=sum(x["status"]=="evaluable_ohlcv" for x in observed)
    signals=[x["verified_prebreakout_setup"] for x in observed if x.get("verified_prebreakout_setup")]
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
            "validated_prebreakout_setups":len(signals),"signals":signals,
            "observations":observed}


def merge_slots(current, previous, now, ttl_hours=96):
    """Merge only recent, independently collected OHLCV. Never revive stale setups."""
    from datetime import timedelta
    if not isinstance(previous,dict) or previous.get("schema")!=current.get("schema"):
        return current
    cutoff=now-timedelta(hours=ttl_hours)
    observations={}
    for entry in previous.get("observations",[]):
        if not isinstance(entry,dict):continue
        ticker=str(entry.get("ticker") or "").strip().upper()
        timestamp=entry.get("ohlcv_observed_at") or previous.get("generated_at")
        try:
            seen=datetime.fromisoformat(str(timestamp).replace("Z","+00:00"))
        except (TypeError,ValueError):
            continue
        if not ticker or seen.tzinfo is None or not cutoff<=seen<=now+timedelta(hours=1):
            continue
        observations[ticker]=entry
    for entry in current.get("observations",[]):
        if isinstance(entry,dict) and entry.get("ticker"):
            observations[str(entry["ticker"]).strip().upper()]=entry
    all_rows=list(observations.values())
    signals=[row["verified_prebreakout_setup"] for row in all_rows
             if row.get("status")=="evaluable_ohlcv"
             and isinstance(row.get("verified_prebreakout_setup"),dict)]
    evaluable=sum(row.get("status")=="evaluable_ohlcv" for row in all_rows)
    count=current.get("universe_100m_500m_count") or 0
    return {**current,"observations":all_rows,"signals":signals,
            "evaluable_ohlcv":evaluable,"observed_incomplete":len(all_rows)-evaluable,
            "not_observed":max(0,count-len(all_rows)),
            "universe_coverage_pct":round(100*evaluable/count,2) if count else None,
            "validated_prebreakout_setups":len(signals),
            "coverage_window_hours":ttl_hours,
            "distinct_tickers_observed":len(all_rows)}

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
    try:
        previous=json.loads(args.output.read_text(encoding="utf-8"))
    except (FileNotFoundError,ValueError,OSError):
        previous={}
    result=merge_slots(result,previous,datetime.fromisoformat(result["generated_at"]))
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k!="observations"}))

if __name__=="__main__":main()
