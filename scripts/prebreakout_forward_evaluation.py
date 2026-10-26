#!/usr/bin/env python3
"""Evaluate archived technical signals against subsequent adjusted daily closes.

This is a point-in-time evaluation helper, NOT a historical reconstruction of signals.
A snapshot is eligible only when its original publication timestamp is available.
"""
from datetime import date, datetime, timezone
from statistics import mean, median
import math

HORIZONS=(5,10,20,60)

def _date(value):
    return date.fromisoformat(str(value)[:10])

def _series(rows):
    result={}
    for bar in rows:
        try:
            d=_date(bar["date"]); p=float(bar["close"])
            if not math.isfinite(p) or p<=0 or d in result: raise ValueError("invalid close or duplicate")
            result[d]=p
        except (KeyError,TypeError,OverflowError) as exc:
            raise ValueError("invalid OHLC date/close") from exc
    return sorted(result.items())

def evaluate(signal, asset_bars, benchmark_bars, horizons=HORIZONS):
    """Start with the first common trading session strictly after signal date.
    All entry and exit prices are adjusted closes; these are NOT executable fills.
    Never pad missing benchmark sessions or forward fill asset prices.
    """
    try:
        day=_date(signal["date"])
        a=dict(_series(asset_bars)); b=dict(_series(benchmark_bars))
    except (KeyError,ValueError,TypeError) as exc:
        raise ValueError("invalid signal or price data") from exc
    # The benchmark defines the session calendar. Intersecting calendars before
    # counting sessions silently stretches a 5-day horizon when an asset bar is
    # missing. Never shift the entry or exit to compensate for missing prices.
    sessions=sorted(b)
    future=[d for d in sessions if d>day]
    if not future:return {"ticker":signal.get("ticker"),"entry":None,"results":{}}
    entry=future[0]; index=sessions.index(entry)
    results={}
    for h in horizons:
        if not isinstance(h,int) or h<1:raise ValueError("invalid horizon")
        end=index+h
        if end>=len(sessions):results[h]=None;continue
        window=sessions[index:end+1]
        if any(d not in a for d in window):
            results[h]=None
            continue
        exit_day=sessions[end]
        r=a[exit_day]/a[entry]-1
        bench=b[exit_day]/b[entry]-1
        prices=[a[d]/a[entry]-1 for d in window]
        results[h]={"exit":exit_day.isoformat(),"return":r,"spy_return":bench,
                    "excess_return":r-bench,"max_adverse_excursion":min(prices)}
    return {"ticker":signal.get("ticker"),"entry":entry.isoformat(),"results":results}

def evaluate_archived(snapshot, ticker, asset_bars, benchmark_bars, horizons=HORIZONS):
    """Evaluate only a verifiably published signal from its first subsequent session.

    Never use the signal's market session as the executable entry when a later
    publication timestamp is known. Empty or unpublished feed means no evidence.
    """
    if snapshot.get("schema")!="vestra_prebreakout_v1" or not isinstance(snapshot.get("signals"),list):
        raise ValueError("invalid archived snapshot")
    try:
        published=datetime.fromisoformat(str(snapshot["generated_at"]).replace("Z","+00:00"))
    except (KeyError, ValueError, TypeError) as exc:
        raise ValueError("missing or invalid published timestamp") from exc
    if published.tzinfo is None:raise ValueError("publication timezone missing")
    publication_day=published.astimezone(timezone.utc).date()
    matches=[s for s in snapshot["signals"] if s.get("ticker")==ticker]
    if len(matches)!=1:raise ValueError("ticker missing or duplicated in archived publication")
    original=matches[0]
    try:
        signal_day=_date(original["date"])
    except (KeyError,ValueError,TypeError) as exc:
        raise ValueError("invalid signal date") from exc
    if signal_day>publication_day:raise ValueError("future-dated signal")
    # Start strictly after both the original session and actual publication day.
    delayed={**original,"date":max(signal_day,publication_day).isoformat()}
    outcome=evaluate(delayed,asset_bars,benchmark_bars,horizons=horizons)
    outcome["published_at"]=published.isoformat()
    outcome["signal_date"]=signal_day.isoformat()
    outcome["stage"]=original.get("stage")
    return outcome

def aggregate(evaluations,horizons=HORIZONS):
    output={}
    for h in horizons:
        items=[e["results"].get(h) for e in evaluations if e.get("results")]
        usable=[x for x in items if x is not None]
        output[h]={"n":len(usable),"n_missing":len(items)-len(usable)}
        if usable:
            output[h].update({"hit_rate":mean(x["return"]>0 for x in usable),
                "mean_return":mean(x["return"] for x in usable),
                "median_excess_return":median(x["excess_return"] for x in usable),
                "mean_max_adverse_excursion":mean(x["max_adverse_excursion"] for x in usable)})
    return output
