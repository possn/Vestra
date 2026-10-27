#!/usr/bin/env python3
"""Retrieve adjusted *completed* daily closes for archived point-in-time cohorts.

Data come from independent Yahoo Finance historical downloads (auto_adjust=True).
Never backfill scanner signals; never evaluate intraday unfinished bars.
A failed price download is an error, not zero performance.
"""
from __future__ import annotations
import argparse
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from build_prebreakout_forward_cohorts import cohorts, build

ROOT=Path(__file__).resolve().parents[1]

def completed_bars(frame, today):
    """Normalize a Yahoo frame to an unambiguous UTC-date daily close series."""
    if frame is None or getattr(frame,"empty",True):
        raise ValueError("missing price history")
    result=[]; dates=set()
    if "Close" not in frame.columns:raise ValueError("missing adjusted Close")
    for stamp, row in frame.iterrows():
        day=stamp.date()
        if day>=today:continue   # current UTC session may still be forming
        value=float(row["Close"])
        if day in dates or not math.isfinite(value) or value<=0:
            raise ValueError("duplicate or invalid adjusted closing price")
        dates.add(day)
        result.append({"date":day.isoformat(),"close":value})
    if not result:raise ValueError("no completed daily prices")
    return sorted(result,key=lambda x:x["date"])

def completed_ohlcv(frame,today):
    """Return complete adjusted OHLCV or None; never synthesize missing fields."""
    if frame is None or getattr(frame,"empty",True):
        return None
    if not all(k in frame.columns for k in ("Close","High","Low","Volume")):
        return None
    result=[];days=set()
    for stamp,row in frame.iterrows():
        day=stamp.date()
        if day>=today:continue
        try:
            close,high,low,volume=(float(row[k]) for k in ("Close","High","Low","Volume"))
        except (KeyError,TypeError,ValueError,OverflowError):
            return None
        if (day in days or not all(math.isfinite(v) for v in (close,high,low,volume))
                or not 0<low<=close<=high or volume<=0):
            return None
        days.add(day)
        result.append({"date":day.isoformat(),"close":close,"high":high,"low":low,"volume":volume})
    return sorted(result,key=lambda x:x["date"]) if result else None

def gather(archive:Path, downloader, now=None):
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None:raise ValueError("UTC clock required")
    today=now.astimezone(timezone.utc).date()
    items=cohorts(archive)
    if not items:raise ValueError("no immutable historical cohorts")
    earliest=min(datetime.fromisoformat(c["published_at"]).date() for c in items)
    # A forward breakout needs 20 *prior* completed volume sessions; preserve a full historical buffer.
    start=(earliest-timedelta(days=90)).isoformat()
    end=(today+timedelta(days=1)).isoformat()
    tickers=sorted(set(c["ticker"] for c in items)|{"SPY"})
    prices={}; event_prices={}; failures={}
    recovered_after_retry=[]
    for ticker in tickers:
        # One bounded retry for intermittent Yahoo empty/error frames.
        # Identical source, date range, adjustment rules; no substitute data.
        for attempt in (1,2):
            try:
                frame=downloader(ticker,start=start,end=end,auto_adjust=True,
                                 progress=False,threads=False,multi_level_index=False)
                close_rows=completed_bars(frame,today)
                ohlcv=completed_ohlcv(frame,today)
                prices[ticker]=close_rows
                if ohlcv is not None:event_prices[ticker]=ohlcv
                if attempt==2:recovered_after_retry.append(ticker)
                break
            except Exception as exc:
                if attempt==2:failures[ticker]=type(exc).__name__
    if "SPY" not in prices:
        raise ValueError("benchmark SPY adjusted closes unavailable")
    results=build(archive,prices,prices["SPY"],event_prices=event_prices)
    results["price_metadata"]={"provider":"yahoo_finance","auto_adjust":True,
        "completed_before_utc_date":today.isoformat(),"benchmark":"SPY",
        "downloaded":len(prices),"complete_ohlcv":len(event_prices),"failed":failures,
        "recovered_after_single_retry":sorted(recovered_after_retry),
        "retry_policy":"at_most_two_same_source_requests_only_on_download_or_close_failure"}
    return results

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--archive",type=Path,default=ROOT/"data/prebreakout-history")
    parser.add_argument("--output",type=Path,default=ROOT/"data/prebreakout-forward-evidence.json")
    args=parser.parse_args()
    import yfinance as yf
    result=gather(args.archive,yf.download)
    args.output.write_text(json.dumps(result,ensure_ascii=False,allow_nan=False,indent=2)+"\n",encoding="utf-8")
    print(f"Evaluated {result['cohort_count']} archived cohorts")

if __name__=="__main__":
    main()
