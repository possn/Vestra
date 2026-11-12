#!/usr/bin/env python3
"""Independent, bounded *observed* OHLCV collector for USD 100m–500m small caps.

Research output only. Never writes production signals or modifies quote engines.
Missing data and uncertain currencies are failures, not zeroes or signals.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from collections import Counter
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
    """Fail closed on ticker collisions, including non-equity/other-cap rows.

    A bare ticker cannot establish issuer/listing identity when the source
    index contains multiple records under that name. Do not select a winner
    based on source ordering or on the largest market cap.
    """
    found={}
    seen=set()
    ambiguous=set()
    for row in rows:
        if not isinstance(row,dict):continue
        symbol=str(row.get("ticker") or "").strip().upper()
        if not symbol:continue
        if symbol in seen:
            ambiguous.add(symbol)
        seen.add(symbol)
        cap=row.get("market_cap")
        kind=str(row.get("quote_type") or "").upper()
        if (kind in {"ETF","FUND","MUTUALFUND","CRYPTO"}
            or type(cap) not in (int,float) or not math.isfinite(cap)
            or not 100_000_000<=cap<500_000_000):continue
        found[symbol]=float(cap)
    return sorted(set(found)-ambiguous)

def inspect(ticker,frame,currency,checked_at):
    if currency!="USD":
        return {"ticker":ticker,"status":"currency_not_verified_usd","currency":currency}
    if frame is None or getattr(frame,"empty",True):
        return {"ticker":ticker,"status":"no_ohlcv"}
    clean=[]
    full_bars=[]
    zero_volume_sessions=0
    # A no-trade day is a gap in evidence, not a valid liquidity bar.
    # Only a new uninterrupted >=220-session segment may be screened.
    try:
        for timestamp,row in frame.iterrows():
            day=timestamp.date().isoformat()
            # A bar stamped today may reflect an unfinished trading session.
            # Exclude it conservatively instead of treating partial volume as final.
            if day == checked_at.date().isoformat():
                continue
            fields=("Open","High","Low","Close","Volume")
            # Boolean values are not observed trade prices or share volume.
            if any(isinstance(row[k], bool) or (type(row[k]).__module__.startswith("numpy") and type(row[k]).__name__ in ("bool", "bool_")) for k in fields):
                return {"ticker":ticker,"status":"invalid_ohlcv"}
            values=[float(row[k]) for k in fields]
            o,h,l,c,v=values
            if not all(map(math.isfinite,values)) or not (0<l<=min(o,c)<=max(o,c)<=h and v>=0):
                return {"ticker":ticker,"status":"invalid_ohlcv"}
            if full_bars and day<=full_bars[-1]['date']:
                return {"ticker":ticker,"status":"unordered_or_duplicate_sessions"}
            full_bars.append({'date':day,'open':o,'high':h,'low':l,'close':c,'volume':v})
            if v==0:
                zero_volume_sessions+=1
                clean=[]  # Do not bridge a zero-volume bar in the VCP window.
            else:
                clean.append((day,c,v))
    except (KeyError,TypeError,ValueError,OverflowError,AttributeError):
        return {"ticker":ticker,"status":"invalid_ohlcv"}
    if len(clean)<MIN_BARS:
        return {"ticker":ticker,
                "status":"zero_volume_interrupted_history" if zero_volume_sessions else "insufficient_ohlcv",
                "bars":len(clean),"zero_volume_sessions":zero_volume_sessions,
                "research_only":True,"setup_blocked":True}
    if zero_volume_sessions:
        # The previous segment is not allowed to create an artificial
        # continuity bridge, even though it may be retained for provenance.
        full_bars=full_bars[-len(clean):]
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
            "zero_volume_sessions_before_contiguous_window":zero_volume_sessions,
            "verified_prebreakout_setup":setup,
            "first_session":clean[0][0],"last_session":last,
            "average_dollar_volume_20_usd":round(turnover,2),
            "liquidity_5m_usd_verified":turnover>=5_000_000,
            "spread_verified":False,"gap_risk_not_assessed":True,
            "currency":"USD","price_basis":"yfinance_auto_adjusted",
            "ohlcv_observed_at":checked_at.isoformat()}

def pick_research_tickers(names,slot,budget,previous,checked_at,ttl_hours=96):
    """Prioritize CURRENT universe names absent from the recent observed window.

    Keep the old cyclic slot order as a deterministic tiebreaker; once every
    eligible name has been observed, revisit the oldest evidence first.
    This changes WHICH names are queried, never the OHLCV eligibility gate.
    """
    from datetime import timedelta
    if not names:return []
    start=(slot*budget)%len(names)
    rotated=names[start:]+names[:start]
    if not isinstance(previous,dict) or previous.get("schema")!="vestra_breakout_lab_smallcap_ohlcv_research_v1":
        return rotated[:min(budget,len(names))]
    cutoff=checked_at-timedelta(hours=ttl_hours)
    last_seen={}
    last_status={}
    for row in previous.get("observations",[]):
        if not isinstance(row,dict):continue
        ticker=str(row.get("ticker") or "").strip().upper()
        if ticker not in names:continue
        raw=row.get("observation_checked_at") or row.get("ohlcv_observed_at") or previous.get("generated_at")
        try:stamp=datetime.fromisoformat(str(raw).replace("Z","+00:00"))
        except (TypeError,ValueError):continue
        if stamp.tzinfo is None:continue
        stamp=stamp.astimezone(timezone.utc)
        if not cutoff<=stamp<=checked_at:continue
        if stamp>=last_seen.get(ticker,cutoff):
            last_seen[ticker]=stamp
            # Older reports omitted status, so preserve their original rotation
            # priority rather than treating legacy evidence as a provider failure.
            last_status[ticker]=row.get("status","evaluable_ohlcv")
    # Never-observed names first. Once they are exhausted, retry recent
    # non-evaluable requests before refreshing already usable OHLCV evidence.
    # Provider errors do not count as verified bars, yet are not allowed to
    # starve entirely unseen names on repeated collection slots.
    ordered=sorted(rotated,key=lambda ticker:(
        0 if ticker not in last_seen else
        (1 if last_status.get(ticker)!="evaluable_ohlcv" else 2),
        last_seen.get(ticker,cutoff)))
    return ordered[:min(budget,len(names))]


def collect(rows,provider,slot=0,budget=20,checked_at=None,*,previous=None):
    if type(slot)!=int or slot<0 or type(budget)!=int or not 1<=budget<=MAX_PER_RUN:
        raise ValueError("slot must be >=0 and budget between 1 and 30")
    checked_at=checked_at or datetime.now(timezone.utc)
    if checked_at.tzinfo is None:raise ValueError("checked_at must be timezone-aware")
    names=cohort(rows)
    # Stable identity of the eligible ticker population; a change in the
    # denominator alone must never be presented as coverage improvement.
    cohort_sha256=hashlib.sha256("\n".join(names).encode("utf-8")).hexdigest()
    selected=pick_research_tickers(names,slot,budget,previous,checked_at)
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
    attempt_status_counts=dict(sorted(Counter(x["status"] for x in observed).items()))
    provider_error_type_counts=dict(sorted(Counter(x["error_type"] for x in observed
        if x["status"]=="provider_error" and x.get("error_type")).items()))
    signals=[x["verified_prebreakout_setup"] for x in observed if x.get("verified_prebreakout_setup")]
    return {"schema":"vestra_breakout_lab_smallcap_ohlcv_research_v1",
            "status":"observed_research_only_not_breakout_signals",
            "generated_at":checked_at.isoformat(),"source":"yfinance",
            "universe_100m_500m_count":len(names),"universe_tickers_sha256":cohort_sha256,"slot":slot,"budget":budget,
            "provider_tickers_attempted":len(observed),
            "provider_attempt_status_counts":attempt_status_counts,
            "provider_error_type_counts":provider_error_type_counts,
            "evaluable_ohlcv":evaluable,"observed_incomplete":len(observed)-evaluable,
            "not_observed":len(names)-len(observed),
            "universe_coverage_pct":round(100*evaluable/len(names),2) if names else None,
            "point_in_time_caveat":"market_caps_from_current_index_not_historical_asof_snapshots",
            "not_breakout_candidates":True,"no_success_probability":True,
            "validated_prebreakout_setups":len(signals),"signals":signals,
            "observations":observed}


def merge_slots(current, previous, now, ttl_hours=96, *, eligible_tickers=None):
    """Merge only recent, independently collected OHLCV. Never revive stale setups."""
    from datetime import timedelta
    if not isinstance(previous,dict) or previous.get("schema")!=current.get("schema"):
        return current
    cutoff=now-timedelta(hours=ttl_hours)
    eligible=set(eligible_tickers) if eligible_tickers is not None else None
    count=current.get("universe_100m_500m_count") or 0
    if eligible is not None and len(eligible)!=count:
        raise ValueError("current smallcap universe count and identities disagree")
    excluded_outside_current_universe=0
    observations={}
    for entry in previous.get("observations",[]):
        if not isinstance(entry,dict):continue
        ticker=str(entry.get("ticker") or "").strip().upper()
        timestamp=entry.get("observation_checked_at") or entry.get("ohlcv_observed_at") or previous.get("generated_at")
        try:
            seen=datetime.fromisoformat(str(timestamp).replace("Z","+00:00"))
        except (TypeError,ValueError):
            continue
        if not ticker or seen.tzinfo is None or not cutoff<=seen<=now:
            continue
        if eligible is not None and ticker not in eligible:
            excluded_outside_current_universe+=1
            continue
        # Legacy rows without per-ticker timestamps are anchored to the
        # previous file generation ONCE; never refresh their evidence age merely
        # because a later batch publishes another symbol.
        observations[ticker]={**entry,"observation_checked_at":seen.astimezone(timezone.utc).isoformat()}
    for entry in current.get("observations",[]):
        if isinstance(entry,dict) and entry.get("ticker"):
            ticker=str(entry["ticker"]).strip().upper()
            if eligible is not None and ticker not in eligible:
                raise ValueError("observed smallcap ticker outside current eligible universe")
            observations[ticker]={**entry,"observation_checked_at":now.isoformat()}
    all_rows=list(observations.values())
    # Research coverage is a rolling 96h observation window, not proof that a
    # setup is still actionable. A prior setup may only remain in the current
    # signals list within its shorter 18h verification window.
    signal_cutoff=now-timedelta(hours=18)
    signals=[]
    historical_setups_excluded=0
    for row in all_rows:
        setup=row.get("verified_prebreakout_setup")
        if row.get("status")!="evaluable_ohlcv" or not isinstance(setup,dict):
            continue
        raw_timestamp=(row.get("observation_checked_at") or
                       row.get("ohlcv_observed_at"))
        try:
            verified=datetime.fromisoformat(str(raw_timestamp).replace("Z","+00:00"))
        except (TypeError,ValueError):
            verified=None
        if (verified is None or verified.tzinfo is None or
            not signal_cutoff<=verified<=now):
            historical_setups_excluded+=1
            continue
        signals.append(setup)
    evaluable=sum(row.get("status")=="evaluable_ohlcv" for row in all_rows)
    return {**current,"observations":all_rows,"signals":signals,
            "evaluable_ohlcv":evaluable,"observed_incomplete":len(all_rows)-evaluable,
            "not_observed":max(0,count-len(all_rows)),
            "universe_coverage_pct":round(100*evaluable/count,2) if count else None,
            "validated_prebreakout_setups":len(signals),
            "setup_verification_window_hours":18,
            "historical_setups_excluded_as_stale":historical_setups_excluded,
            "coverage_window_hours":ttl_hours,
            "distinct_tickers_observed":len(all_rows),
            "excluded_outside_current_universe":excluded_outside_current_universe}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--slot",type=int,default=0)
    parser.add_argument("--budget",type=int,default=20)
    parser.add_argument("--output",type=Path,default=DEFAULT_OUTPUT)
    args=parser.parse_args()
    import yfinance as yf
    index_path=ROOT/"data/stocks-index.json"
    index_bytes=index_path.read_bytes()
    rows=json.loads(index_bytes).get("stocks",[])
    args.output.parent.mkdir(parents=True,exist_ok=True)
    try:
        previous=json.loads(args.output.read_text(encoding="utf-8"))
    except (FileNotFoundError,ValueError,OSError):
        previous={}
    result=collect(rows,yf,args.slot,args.budget,previous=previous)
    result["universe_source_index_sha256"]=hashlib.sha256(index_bytes).hexdigest()
    result=merge_slots(result,previous,datetime.fromisoformat(result["generated_at"]),
                       eligible_tickers=cohort(rows))
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k!="observations"}))

if __name__=="__main__":main()
