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

def scan_bars(ticker: str, bars: list[dict], today: date|None=None):
    today=today or datetime.now(timezone.utc).date()
    clean=[b for b in bars if isinstance(b.get("close"),(int,float)) and math.isfinite(b["close"]) and b["close"]>0]
    if len(clean)<211:return None
    end=len(clean)-1
    try:latest=date.fromisoformat(str(clean[-1]["date"])[:10])
    except (ValueError,TypeError):return None
    age=(today-latest).days
    if age< -1 or age>7:return None
    values=[b["close"] for b in clean]
    m50=sma(values,end,50);m150=sma(values,end,150);m200=sma(values,end,200)
    slopes=[m50-sma(values,end-10,50),m150-sma(values,end-10,150),m200-sma(values,end-10,200)]
    if not (values[-1]>m150 and m50>m200 and all(x>0 for x in slopes)):return None
    def bounds(part):
        highs=[b.get("high") if isinstance(b.get("high"),(float,int)) and b.get("high")>0 else b["close"] for b in part]
        lows=[b.get("low") if isinstance(b.get("low"),(float,int)) and b.get("low")>0 else b["close"] for b in part]
        return max(highs),min(lows)
    recent=clean[-40:]; earlier=clean[-100:-60]
    if len(earlier)<40:return None
    hi,lo=bounds(recent);old_hi,old_lo=bounds(earlier)
    width=hi/lo-1;old_width=old_hi/old_lo-1
    if not (old_width>0 and width<old_width*.8 and width<=.22):return None
    resistance=bounds(recent[:-1])[0]
    distance=(resistance/values[-1]-1)*100
    if distance>8:return None
    v=[b.get("volume") for b in clean[-21:-1]]
    avg_volume=sum(v)/20 if len(v)==20 and all(isinstance(x,(int,float)) and math.isfinite(x) and x>0 for x in v) else None
    last_volume=clean[-1].get("volume")
    volume_ok=avg_volume is not None and isinstance(last_volume,(int,float)) and math.isfinite(last_volume) and last_volume>=avg_volume*1.5
    golden=sma(values,end-20,50)<=sma(values,end-20,200)
    confirmed=values[-1]>resistance*1.005 and volume_ok
    stage="confirmado" if confirmed else "pré-breakout" if -1.5<=distance<=4 else "compressão"
    score=round(min(100,45+min(18,(1-width/old_width)*30)+max(0,8-max(0,distance))*2+(8 if golden else 0)+(7 if volume_ok else 0)))
    return {"ticker":ticker,"date":latest.isoformat(),"stage":stage,"score":score,
            "widthPct":round(width*100,2),"priorWidthPct":round(old_width*100,2),
            "distancePct":round(distance,2),"resistance":round(resistance,5),
            "sma50":round(m50,5),"sma150":round(m150,5),"sma200":round(m200,5),
            "volumeConfirmed":bool(volume_ok),"goldenCrossRecent":bool(golden),
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
    try:old=json.loads(OUTPUT.read_text(encoding="utf-8")).get("signals",[])
    except (FileNotFoundError,ValueError):old=[]
    by={s["ticker"]:s for s in old if isinstance(s,dict) and s.get("ticker") and
        s.get("source")=="yahoo:daily_ohlcv" and
        isinstance(s.get("date"),str) and 0<=(now.date()-date.fromisoformat(s["date"])).days<=3}
    for signal in found:by[signal["ticker"]]=signal
    payload={"schema":"vestra_prebreakout_v1","generated_at":now.isoformat(),
             "attempted":len(tickers),"with_ohlcv":checked,"new_signals":len(found),
             "errors":failures[:8],"signals":sorted(by.values(),key=lambda s:(-s["score"],s["ticker"]))[:75]}
    OUTPUT.write_text(json.dumps(payload,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in payload.items() if k!="signals"}))

if __name__=="__main__":main()
