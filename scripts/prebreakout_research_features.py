#!/usr/bin/env python3
"""Research-only historical pre-breakout features, never production probabilities.

Only bars strictly BEFORE the UTC publication calendar date are admitted.
This deliberately omits same-day bars even for after-close publications.
Adjusted historical OHLCV may be restated by data providers: features from
such archives are retrospective hypotheses, not verified point-in-time data.
"""
from __future__ import annotations
from datetime import datetime, timezone
import math

def _eligible(bars, publication):
    try:
        cutoff=datetime.fromisoformat(publication.replace("Z","+00:00"))
        if cutoff.tzinfo is None:
            return []
        day=cutoff.astimezone(timezone.utc).date().isoformat()
    except (ValueError, TypeError, AttributeError):
        return []
    selected={}
    for bar in bars if isinstance(bars,list) else []:
        if not isinstance(bar,dict):continue
        date=str(bar.get("date",""))[:10]
        if not (len(date)==10 and date<day):continue
        try:
            dt=datetime.fromisoformat(date).date()
            h,l,c,v=(float(bar[k]) for k in ("high","low","close","volume"))
            if not all(math.isfinite(x) for x in (h,l,c,v)) or l<=0 or c<=0 or h<l or v<0:continue
        except (ValueError,TypeError,KeyError):continue
        if date in selected:return []  # Do not choose arbitrarily among duplicate market bars.
        selected[date]=(h,l,c,v)
    return sorted(selected.items())

def research_features(stock_bars,spy_bars,published_at):
    """Exploratory as-of-publication candidates; no imputation or fitted score."""
    stock=_eligible(stock_bars,published_at)
    spy=_eligible(spy_bars,published_at)
    result={"method":"historical_prior_calendar_day_only","published_at":published_at,
            "point_in_time_adjustments_verified":False,
            "predictive_validity_established":False,
            "features":{},"missing":[]}
    if len(stock)<21:
        result["missing"].append("stock_minimum_21_prior_bars")
        return result
    tail=stock[-21:]
    closes=[row[1][2] for row in tail]
    values=[row[1] for row in tail]
    true_ranges=[max(v[0]-v[1],abs(v[0]-closes[i-1]),abs(v[1]-closes[i-1]))
                 for i,v in enumerate(values) if i>0]
    atr=sum(true_ranges[-14:])/14
    result["features"]["atr14_pct"]=round(100*atr/closes[-1],6)
    previous_volumes=[v[3] for v in values[-20:-5]]
    recent_volumes=[v[3] for v in values[-5:]]
    denominator=sum(previous_volumes)/len(previous_volumes)
    if denominator>0:
        result["features"]["recent5_vs_prior15_volume_ratio"]=round(
            (sum(recent_volumes)/len(recent_volumes))/denominator,6)
    else:result["missing"].append("zero_prior_volume")
    result["features"]["stock_return_20_sessions"]=round(closes[-1]/closes[0]-1,8)
    benchmark=dict(spy)
    aligned=[(d,row[2],benchmark[d][2]) for d,row in tail if d in benchmark]
    if len(aligned)==21:
        result["features"]["relative_return_20_vs_spy"]=round(
            aligned[-1][1]/aligned[0][1]-aligned[-1][2]/aligned[0][2],8)
    else:result["missing"].append("spy_21_aligned_sessions")
    return result
