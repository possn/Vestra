#!/usr/bin/env python3
"""Prospective breakout-event observation from immutable published signal metadata.

Research only: excludes signal/publication sessions and demands complete daily OHLCV.
This does not imply executable trades or a calibrated probability.
"""
from datetime import datetime, timezone, date
import math

def breakout_event(snapshot:dict, ticker:str, bars:list[dict], horizon:int=20):
    if type(horizon) is not int or horizon<1:
        raise ValueError("invalid horizon")
    if snapshot.get("schema")!="vestra_prebreakout_v1" or not isinstance(snapshot.get("signals"),list):
        raise ValueError("invalid snapshot")
    published=datetime.fromisoformat(str(snapshot["generated_at"]).replace("Z","+00:00"))
    if published.tzinfo is None:
        raise ValueError("timezone required")
    matches=[r for r in snapshot["signals"] if r.get("ticker")==ticker]
    if len(matches)!=1:
        raise ValueError("missing or duplicate ticker")
    signal=matches[0]
    pivot=float(signal["resistance"])
    if not math.isfinite(pivot) or pivot<=0:
        raise ValueError("invalid pivot")
    first_eligible=max(date.fromisoformat(str(signal["date"])[:10]),published.astimezone(timezone.utc).date())
    clean=[]
    for row in bars:
        d=date.fromisoformat(str(row["date"])[:10])
        values=[float(row[k]) for k in ("close","high","low","volume")]
        close,high,low,volume=values
        if not all(math.isfinite(v) for v in values) or not 0<low<=close<=high or volume<=0:
            raise ValueError("invalid daily OHLCV")
        if clean and d<=clean[-1][0]:
            raise ValueError("bars not strictly ordered")
        clean.append((d,close,high,low,volume))
    indices=[i for i,r in enumerate(clean) if r[0]>first_eligible]
    if not indices:
        return {"status":"pending","observed_sessions":0,"event_date":None}
    observed=indices[:horizon]
    for i in observed:
        if i<20:
            return {"status":"missing_history","observed_sessions":0,"event_date":None}
        day,close,high,low,volume=clean[i]
        prior_volume=sum(r[4] for r in clean[i-20:i])/20
        close_location=(close-low)/(high-low) if high>low else 0
        if close>pivot*1.005 and close_location>=.75 and volume>=1.5*prior_volume:
            return {"status":"confirmed","observed_sessions":observed.index(i)+1,
                    "event_date":day.isoformat()}
    return {"status":"not_confirmed" if len(observed)>=horizon else "pending",
            "observed_sessions":len(observed),"event_date":None}
