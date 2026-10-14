#!/usr/bin/env python3
"""Bounded daily pre-breakout scan: verified Yahoo OHLCV, never an entry recommendation."""
from __future__ import annotations
import json
import math
from datetime import datetime, timezone, date
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
INDEX=ROOT/"data"/"stocks-index.json"
OUTPUT=ROOT/"data"/"prebreakout-signals.json"

def sma(values: list[float], end: int, span: int):
    return sum(values[end-span+1:end+1])/span if end-span+1>=0 else None

def strong_breakout_close(current: float, previous: float, resistance: float, high: float, low: float, volume_confirmed: bool) -> bool:
    """Demand an upside break on confirmed volume with a close in the top 25% of the daily range."""
    if not all(math.isfinite(x) for x in (current, previous, resistance, high, low)):
        return False
    return (volume_confirmed and low < high and low <= current <= high
            and current > previous and current > resistance * 1.005
            and (current-low)/(high-low) >= .75)

def scan_bars(ticker: str, bars: list[dict], today: date|None=None):
    """Identify a contracting base, not a prediction of future returns."""
    today=today or datetime.now(timezone.utc).date()
    clean=[]
    for bar in bars:
        try:
            day=date.fromisoformat(str(bar["date"])[:10])
            close=float(bar["close"]);high=float(bar["high"]);low=float(bar["low"])
        except (KeyError,ValueError,TypeError,OverflowError):
            return None  # Missing OHLC cannot silently become close-only evidence.
        if not all(math.isfinite(v) for v in (close,high,low)):
            return None
        if not (0<low<=close<=high):
            return None
        if clean and day<=clean[-1]["day"]:
            return None  # Reject duplicated or out-of-order sessions.
        clean.append({**bar,"day":day,"close":close,"high":high,"low":low})
    if len(clean)<220:return None
    latest=clean[-1]["day"]
    age=(today-latest).days
    if not 0<=age<=7:return None
    end=len(clean)-1
    values=[b["close"] for b in clean]
    m50=sma(values,end,50);m150=sma(values,end,150);m200=sma(values,end,200)
    slopes=[m50-sma(values,end-10,50),m150-sma(values,end-10,150),m200-sma(values,end-10,200)]
    if not (values[-1]>m150 and m50>m200 and all(x>0 for x in slopes)):return None
    def bounds(part):
        return max(b["high"] for b in part),min(b["low"] for b in part)
    def width(part):
        high,low=bounds(part)
        return high/low-1
    # Require sequential, non-overlapping contractions, not merely one quieter 40-day window.
    prior=clean[-100:-60];first=clean[-60:-40];second=clean[-40:-20];third=clean[-20:]
    old_width=width(prior);w1=width(first);w2=width(second);w3=width(third)
    base_width=width(clean[-40:])
    if not (old_width>0 and base_width<=.22 and base_width<old_width*.8):
        return None
    vcp=w1>0 and w2<=w1*.85 and w3<=w2*.85
    if not vcp:return None
    resistance=bounds(clean[-40:-1])[0]
    current=values[-1]
    distance=(resistance/current-1)*100
    if distance>8 or distance< -5:return None  # Too far below pivot, or already extended.
    prior_volumes=[]
    recent_volumes=[]
    for part,target in ((clean[-50:-10],prior_volumes),(clean[-10:],recent_volumes)):
        for bar in part:
            v=bar.get("volume")
            if not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0:
                target.append(None)
            else:
                target.append(float(v))
    # Drying volume is evidence for pre-breakout; never infer it from missing bars.
    baseline=sum(prior_volumes)/len(prior_volumes) if all(v is not None for v in prior_volumes) else None
    quiet=sum(recent_volumes[:-1])/9 if all(v is not None for v in recent_volumes[:-1]) else None
    volume_dry=baseline is not None and quiet is not None and quiet<=baseline*.80
    reference=clean[-21:-1]
    mean_vol=sum(float(b["volume"]) for b in reference)/20 if all(isinstance(b.get("volume"),(int,float)) and math.isfinite(b["volume"]) and b["volume"]>0 for b in reference) else None
    volume_confirmed=mean_vol is not None and recent_volumes[-1] is not None and recent_volumes[-1]>=mean_vol*1.5
    crossed=any(sma(values,i-1,50)<=sma(values,i-1,200) and sma(values,i,50)>sma(values,i,200) for i in range(end-19,end+1))
    # Crossing proximity is only reported once the main MM50 > MM200 eligibility permits it.
    near_cross=False
    # Only a rising closing price with a verified 1.5x volume expansion confirms the breakout.
    breakout=strong_breakout_close(current,values[-2],resistance,clean[-1]["high"],clean[-1]["low"],volume_confirmed)
    if not breakout and distance< -1.5:return None
    stage="confirmado" if breakout else "pré-breakout" if 0<=distance<=4 and volume_dry else "compressão"
    contraction=1-w3/max(w1,1e-9)
    score=round(max(0,min(100,35+min(20,contraction*30)+
        (12 if volume_dry else 0)+(12 if 0<=distance<=4 else 0)+
        (10 if crossed else 0)+(11 if breakout else 0)-
        (12 if baseline is None else 0))))
    return {"ticker":ticker,"date":latest.isoformat(),"stage":stage,"score":score,
            "widthPct":round(base_width*100,2),"priorWidthPct":round(old_width*100,2),
            "distancePct":round(distance,2),"resistance":round(resistance,5),
            "sma50":round(m50,5),"sma150":round(m150,5),"sma200":round(m200,5),
            "volumeConfirmed":bool(volume_confirmed),"volumeDry":bool(volume_dry),
            "vcpConfirmed":True,"goldenCrossRecent":bool(crossed),
            "goldenCrossImminent":bool(near_cross),
            "source":"yahoo:daily_ohlcv"}

def candidates(stocks: list[dict], when: date):
    universe={}
    for s in stocks:
        ticker=str(s.get("ticker") or "").strip().upper()
        qt=str(s.get("quote_type") or "").upper()
        cap=s.get("market_cap")
        if not ticker or qt in ("ETF","FUND","MUTUALFUND","CRYPTO") or not isinstance(cap,(int,float)) or cap<500_000_000:
            continue
        universe[ticker]=max(cap,universe.get(ticker,0))
    ordered=sorted(universe,key=lambda t:(-universe[t],t))
    anchors=ordered[:40]
    rest=ordered[40:1600]
    offset=((when-date(2026,10,13)).days*110)%max(1,len(rest))
    rotation=(rest[offset:]+rest[:offset])[:110]
    return anchors+[t for t in rotation if t not in anchors]

def dataframe_bars(frame):
    rows=[]
    if frame is None or getattr(frame,"empty",True):return rows
    for idx,r in frame.iterrows():
        try:
            dt=idx.date().isoformat() if hasattr(idx,"date") else str(idx)[:10]
            close=float(r["Close"])
            if not math.isfinite(close):continue
            def val(key):
                try:
                    n=float(r[key])
                    return n if math.isfinite(n) else None
                except (KeyError,TypeError,ValueError):return None
            rows.append({"date":dt,"close":close,"high":val("High"),"low":val("Low"),"volume":val("Volume")})
        except (KeyError,ValueError,TypeError):continue
    return rows

def main():
    import yfinance as yf
    now=datetime.now(timezone.utc);tickers=candidates(json.loads(INDEX.read_text(encoding="utf-8")).get("stocks",[]),now.date())
    found=[];checked=0;failures=[]
    for start in range(0,len(tickers),15):
        group=tickers[start:start+15]
        try:
            data=yf.download(group,period="18mo",interval="1d",group_by="ticker",auto_adjust=True,threads=False,progress=False,timeout=25)
        except Exception as exc:
            failures.append(type(exc).__name__);continue
        for ticker in group:
            try:
                frame=data[ticker] if len(group)>1 else data
                bars=dataframe_bars(frame);checked+=bool(bars)
                signal=scan_bars(ticker,bars,now.date())
                if signal:found.append(signal)
            except (KeyError,ValueError,TypeError) as exc:failures.append(f"{ticker}:{type(exc).__name__}")
    # Do not retain previously accepted setups after the stricter criteria reject them.
    by={signal["ticker"]:signal for signal in found}
    payload={"schema":"vestra_prebreakout_v1","generated_at":now.isoformat(),
             "attempted":len(tickers),"with_ohlcv":checked,"new_signals":len(found),"quality_model":"vcp_volume_v2",
             "errors":failures[:8],"signals":sorted(by.values(),key=lambda s:(-s["score"],s["ticker"]))[:75]}
    OUTPUT.write_text(json.dumps(payload,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in payload.items() if k!="signals"}))

if __name__=="__main__":main()
