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
    if distance>8 or distance<0:return None  # PRE-breakout only: last close must remain at/below pivot.
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
    # An already-confirmed or intraday-exceeded pivot belongs to a separate breakout
    # follow-up, never the predictive pre-breakout radar. Reject failed breakouts too.
    if breakout or clean[-1]["high"]>resistance*1.005:return None
    stage="pré-breakout" if 0<=distance<=4 and volume_dry else "compressão"
    contraction=1-w3/max(w1,1e-9)
    score=round(max(0,min(100,35+min(20,contraction*30)+
        (12 if volume_dry else 0)+(12 if 0<=distance<=4 else 0)+
        (10 if crossed else 0)-
        (12 if baseline is None else 0))))
    # Diagnostic evidence only: no score, gate, or stage changes.
    close_location=(current-clean[-1]["low"])/(clean[-1]["high"]-clean[-1]["low"]) if clean[-1]["high"]>clean[-1]["low"] else None
    volume_ratio=(recent_volumes[-1]/mean_vol) if mean_vol is not None and recent_volumes[-1] is not None else None
    extension_pct=(current/resistance-1)*100 if resistance>0 else None
    return {"ticker":ticker,"date":latest.isoformat(),"stage":stage,"score":score,
            "widthPct":round(base_width*100,2),"priorWidthPct":round(old_width*100,2),
            "distancePct":round(distance,2),"resistance":round(resistance,5),
            "sma50":round(m50,5),"sma150":round(m150,5),"sma200":round(m200,5),
            "volumeConfirmed":bool(volume_confirmed),"volumeDry":bool(volume_dry),
            "breakoutCloseLocationPct":round(close_location*100,1) if close_location is not None else None,
            "breakoutVolumeRatio":round(volume_ratio,2) if volume_ratio is not None else None,
            "breakoutExtensionPct":round(extension_pct,2) if extension_pct is not None else None,
            "vcpConfirmed":True,"goldenCrossRecent":bool(crossed),
            "goldenCrossImminent":bool(near_cross),
            "source":"yahoo:daily_ohlcv"}

def watched_tickers(now:datetime, path:Path=ROOT/"data/prebreakout-observations.json", limit:int=25)->list[str]:
    """Revisit published candidates; historical status alone is never a live signal."""
    try:
        data=json.loads(path.read_text(encoding="utf-8"))
        if data.get("schema")!="vestra_prebreakout_observations_v1" or data.get("historical_only") is not True:
            return []
        checked=datetime.fromisoformat(str(data["generated_at"]).replace("Z","+00:00"))
        if checked.tzinfo is None or not 0<=(now-checked).total_seconds()/86400<=7:return []
        seen=set();result=[]
        for row in data.get("observations",[]):
            ticker=str(row.get("ticker") or "").strip().upper()
            stamp=datetime.fromisoformat(str(row["observed_at"]).replace("Z","+00:00"))
            if (not ticker or ticker in seen or stamp.tzinfo is None or
                not 0<=(now-stamp).total_seconds()/86400<=7 or
                row.get("current") is not False or row.get("stage") not in ("compressão","pré-breakout","confirmado")):
                continue
            seen.add(ticker);result.append(ticker)
            if len(result)>=limit:break
        return result
    except (OSError,ValueError,TypeError,KeyError,AttributeError):
        return []

def candidates(stocks: list[dict], when: date, slot: int = 0, watch: list[str]|None=None):
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
    # Four scheduled scans per day should sample different names, not repeat
    # the same 110 rotating stocks at 02/08/14/20 UTC.
    if not 0<=slot<=3:raise ValueError("invalid six-hour scan slot")
    offset=(((when-date(2026,10,13)).days*4+slot)*110)%max(1,len(rest))
    watchlist=[]
    for ticker in watch or []:
        if ticker in universe and ticker not in anchors and ticker not in watchlist:
            watchlist.append(ticker)
            if len(watchlist)>=25:break
    rotation=[t for t in rest[offset:]+rest[:offset] if t not in anchors and t not in watchlist][:110-len(watchlist)]
    return anchors+watchlist+rotation

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

def completed_sessions(bars, utc_today):
    """Only completed UTC daily sessions are eligible for a verified stage."""
    return [bar for bar in bars if str(bar.get("date") or "")[:10] < utc_today.isoformat()]

def main():
    import yfinance as yf
    now=datetime.now(timezone.utc);tickers=candidates(json.loads(INDEX.read_text(encoding="utf-8")).get("stocks",[]),now.date(),now.hour//6,watched_tickers(now))
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
                bars=completed_sessions(dataframe_bars(frame),now.date());checked+=bool(bars)
                signal=scan_bars(ticker,bars,now.date())
                if signal:found.append(signal)
            except (KeyError,ValueError,TypeError) as exc:failures.append(f"{ticker}:{type(exc).__name__}")
    # Do not retain previously accepted setups after the stricter criteria reject them.
    by={signal["ticker"]:signal for signal in found}
    payload={"schema":"vestra_prebreakout_v1","generated_at":now.isoformat(),
             "attempted":len(tickers),"with_ohlcv":checked,"new_signals":len(found),"quality_model":"vcp_before_pivot_v3","scan_slot_utc":now.hour//6,
             "errors":failures[:8],"signals":sorted(by.values(),key=lambda s:({"pré-breakout":0,"compressão":1}[s["stage"]],-s["score"],s["ticker"]))[:75]}
    OUTPUT.write_text(json.dumps(payload,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in payload.items() if k!="signals"}))

if __name__=="__main__":main()
