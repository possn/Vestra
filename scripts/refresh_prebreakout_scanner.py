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

def historical_breakout_dates(clean: list[dict], start: int, stop: int) -> list[str]:
    """Observed volume-confirmed breaks over a rolling 40-bar high, never an inferred prediction."""
    dates=[]
    for i in range(max(41,start), min(stop,len(clean))):
        ref=clean[i-40:i]
        vols=[b.get("volume") for b in clean[i-20:i+1]]
        if not all(isinstance(v,(int,float)) and math.isfinite(v) and v>0 for v in vols):
            continue
        pivot=max(b["high"] for b in ref)
        bar=clean[i]
        confirmed=vols[-1]>=1.5*(sum(vols[:-1])/20)
        if strong_breakout_close(bar["close"],clean[i-1]["close"],pivot,bar["high"],bar["low"],confirmed):
            dates.append(bar["day"].isoformat())
    return dates

def scan_bars(ticker: str, bars: list[dict], today: date|None=None, *, strict_quality: bool=True, liquidity_floor: float=5_000_000):
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
    if not ((values[-1]>m50>m150>m200 if strict_quality else values[-1]>m150 and m50>m200) and all(x>0 for x in slopes)):return None
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
    # A new signal cannot reuse a base after a confirmed breakout inside its 40-bar window.
    # Older confirmed events are reported as lineage context, not as fresh entry signals.
    if historical_breakout_dates(clean, len(clean)-39, len(clean)-1):
        return None
    earlier_breakouts=historical_breakout_dates(clean, len(clean)-100, len(clean)-40)
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
    tr=[max(b["high"]-b["low"],abs(b["high"]-clean[i-1]["close"]),abs(b["low"]-clean[i-1]["close"])) for i,b in enumerate(clean) if i>0]
    atr14=sum(tr[-14:])/14
    atr60=sum(tr[-60:])/60
    volumes20=[b.get("volume") for b in clean[-20:]]
    dollar_volume20=(sum(b["close"]*v for b,v in zip(clean[-20:],volumes20))/20 if all(isinstance(v,(int,float)) and math.isfinite(v) and v>0 for v in volumes20) else None)
    # Mandatory liquidity and constructive upper-base location: otherwise
    # a thinly traded or weak base can appear deceptively close to a pivot.
    base_high,base_low=bounds(clean[-40:])
    base_position=(current-base_low)/(base_high-base_low) if base_high>base_low else 0
    if strict_quality and (dollar_volume20 is None or dollar_volume20<liquidity_floor or base_position<.65):
        return None
    # The last 10 sessions should not repeatedly close in the weak lower
    # half of the base. Use closed bars only, no forward/market data.
    midpoint=(base_high+base_low)/2
    upper_half_closes=sum(b["close"]>=midpoint for b in clean[-10:])
    support_retention=round(upper_half_closes/10,2)
    diagnostics={"baseUpperHalfCloses10":upper_half_closes,"baseSupportRetention10":support_retention,"atrPct14":round(atr14/current*100,3),"atrContractionRatio":round(atr14/atr60,3) if atr60>0 else None,
                 "averageDollarVolume20":round(dollar_volume20,2) if dollar_volume20 is not None else None,"basePositionPct":round(base_position*100,1),
                 "qualityGates":(["sma50_gt_sma150_gt_sma200","price_above_sma50","dollar_volume20_gte_5m","base_position_gte_65pct"] if strict_quality else [])}
    return {"ticker":ticker,"date":latest.isoformat(),"stage":stage,"score":score,
            "signalClose":round(current,5),"signalPriceBasis":"yahoo_auto_adjusted_asof_publication",
            "widthPct":round(base_width*100,2),"priorWidthPct":round(old_width*100,2),
            "distancePct":round(distance,2),"resistance":round(resistance,5),
            "baseStartDate":clean[-40]["day"].isoformat(),
            "previousConfirmedBreakoutDate":earlier_breakouts[-1] if earlier_breakouts else None,
            "sma50":round(m50,5),"sma150":round(m150,5),"sma200":round(m200,5),
            "volumeConfirmed":bool(volume_confirmed),"volumeDry":bool(volume_dry),
            "breakoutCloseLocationPct":round(close_location*100,1) if close_location is not None else None,
            "breakoutVolumeRatio":round(volume_ratio,2) if volume_ratio is not None else None,
            "breakoutExtensionPct":round(extension_pct,2) if extension_pct is not None else None,
            "vcpConfirmed":True,"goldenCrossRecent":bool(crossed),
            "goldenCrossImminent":bool(near_cross),
            "quantitativeDiagnostics":diagnostics,"source":"yahoo:daily_ohlcv"}

def daily_focus(signals:list[dict], as_of:date)->dict:
    """One evidence-led candidate, or an explicit abstention; never a success probability."""
    eligible=[]
    for row in signals:
        if row.get("stage")!="pré-breakout" or row.get("source")!="yahoo:daily_ohlcv":
            continue
        if row.get("vcpConfirmed") is not True or row.get("volumeDry") is not True:
            continue
        if row.get("volumeConfirmed") is True:
            continue  # This slot is for setups still awaiting a breakout.
        try:
            day=date.fromisoformat(str(row["date"])[:10])
            distance=float(row["distancePct"])
            score=float(row["score"])
        except (KeyError,ValueError,TypeError):
            continue
        if not (0 <= (as_of-day).days <= 4 and math.isfinite(distance) and 0<=distance<=4 and math.isfinite(score) and 0<=score<=100):
            continue
        eligible.append(row)
    if not eligible:
        return {"status":"no_qualified_setup","ticker":None,
                "success_probability":None,"probability_calibrated":False,
                "reason":"no_current_prebreakout_with_verified_contractions_and_drying_volume"}
    # Rank by verified structural quality, not just the legacy heuristic score.
    # Existing eligibility remains unchanged; unavailable diagnostics never earn a bonus.
    def focus_rank(row):
        q=row.get("quantitativeDiagnostics")
        q=q if isinstance(q,dict) else {}
        def verified(name,lower=None,upper=None):
            v=q.get(name)
            if type(v) not in (int,float) or not math.isfinite(v):
                return None
            if lower is not None and v<lower:return None
            if upper is not None and v>upper:return None
            return float(v)
        pos=verified("basePositionPct",0,100)
        contraction=verified("atrContractionRatio",0.01,5)
        liquidity=verified("averageDollarVolume20",0)
        # Prefer candidates tightly positioned near the base high, with
        # contracting ATR and demonstrable liquidity. Heuristic, not calibrated.
        support=verified("baseSupportRetention10",0,1)
        # Resilience is a tie-breaker within the established three-point
        # quality bucket; avoid overpowering stronger evidence or score.
        # Technical readiness precedes excess liquidity. Liquidity above the
        # scanner's mandatory $5m floor is a tie-break, not another signal
        # of likely breakout direction. Avoid double-counting money volume
        # against genuine contraction and constructive base position.
        structural=int(pos is not None and pos>=80)+int(contraction is not None and contraction<=.75)
        resilience=int(support is not None and support>=.8)
        deep_liquidity=int(liquidity is not None and liquidity>=20_000_000)
        return (-structural,-resilience,-deep_liquidity,
                (as_of-date.fromisoformat(str(row["date"])[:10])).days,
                -float(row["score"]),float(row["distancePct"]),row["ticker"])
    best=min(eligible,key=focus_rank)
    return {"status":"research_candidate","ticker":best["ticker"],
            "signal_date":best["date"],"stage":best["stage"],
            "technical_score":best["score"],"distance_to_pivot_pct":best["distancePct"],
            "success_probability":None,"probability_calibrated":False,
            "reason":"ranked_verified_setup_not_a_forecast_or_buy_signal"}

def published_signals_with_focus(signals:list[dict],as_of:date,limit:int=75)->tuple[list[dict],dict]:
    """Keep the featured candidate in the public list even when capped."""
    if limit<1:
        raise ValueError("published signal limit must be positive")
    ordered=sorted(signals,key=lambda row:({"pré-breakout":0,"compressão":1}[row["stage"]],-row["score"],row["ticker"]))
    focus=daily_focus(ordered,as_of)
    visible=ordered[:limit]
    if focus["status"]=="research_candidate" and all(row["ticker"]!=focus["ticker"] for row in visible):
        featured=next(row for row in ordered if row["ticker"]==focus["ticker"])
        visible=sorted(visible[:-1]+[featured],
                       key=lambda row:({"pré-breakout":0,"compressão":1}[row["stage"]],-row["score"],row["ticker"]))
    return visible,focus

def quality_shadow_record(legacy:dict, strict:dict|None)->dict:
    """Research-only point-in-time evidence; never a public recommendation."""
    return {"ticker":legacy["ticker"],"date":legacy["date"],"stage":legacy["stage"],
            "baseStartDate":legacy.get("baseStartDate"),
            "previousConfirmedBreakoutDate":legacy.get("previousConfirmedBreakoutDate"),
            "resistance":legacy["resistance"],"signalClose":legacy["signalClose"],
            "signalPriceBasis":legacy.get("signalPriceBasis"),
            "legacy_eligible":True,"strict_eligible":strict is not None,
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

def eligible_universe_size(stocks: list[dict])->int:
    tickers=set()
    for stock in stocks:
        ticker=str(stock.get("ticker") or "").strip().upper()
        qt=str(stock.get("quote_type") or "").upper()
        cap=stock.get("market_cap")
        if ticker and qt not in ("ETF","FUND","MUTUALFUND","CRYPTO") and isinstance(cap,(int,float)) and math.isfinite(cap) and cap>=500_000_000:
            tickers.add(ticker)
    return len(tickers)

def candidates(stocks: list[dict], when: date, slot: int = 0, watch: list[str]|None=None):
    universe={}
    for s in stocks:
        ticker=str(s.get("ticker") or "").strip().upper()
        qt=str(s.get("quote_type") or "").upper()
        cap=s.get("market_cap")
        if not ticker or qt in ("ETF","FUND","MUTUALFUND","CRYPTO") or not isinstance(cap,(int,float)) or not math.isfinite(cap) or cap<500_000_000:
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

def verified_usd_liquidity(local_turnover, currency, fx, today):
    """Normalize quoted cash turnover to USD; unresolved units/rates fail closed."""
    if not isinstance(local_turnover,(int,float)) or not math.isfinite(local_turnover) or local_turnover<=0:
        return None
    if not isinstance(currency,str) or not currency.strip():
        return None
    unit=currency.strip()
    currency_code="GBP" if unit in ("GBP","GBp","GBX") else unit.upper()
    factor=.01 if unit in ("GBp","GBX") else 1.0
    try:
        reference=date.fromisoformat(str(fx["ecb_reference_date"])[:10])
        rates=fx["rates_to_eur"]
        local=float(rates[currency_code]);usd=float(rates["USD"])
    except (KeyError,ValueError,TypeError,OverflowError):
        return None
    if not 0 <= (today-reference).days <= 7 or not all(math.isfinite(x) and x>0 for x in (local,usd)):
        return None
    return local_turnover*factor*local/usd

def main():
    import yfinance as yf
    now=datetime.now(timezone.utc);tickers=candidates(json.loads(INDEX.read_text(encoding="utf-8")).get("stocks",[]),now.date(),now.hour//6,watched_tickers(now))
    # Coverage refers to this slot, not the entire eligible investment universe.
    eligible=eligible_universe_size(json.loads(INDEX.read_text(encoding="utf-8")).get("stocks",[]))
    found=[];shadow_cases=[];checked=0;failures=[]
    try:
        fx=json.loads((ROOT/"data/fx.json").read_text(encoding="utf-8"))
    except (OSError,ValueError):
        fx={}  # A missing exchange-rate file may never authorize liquidity.
    currency_checked=0;currency_rejected=0
    # Shadow evaluation only; never route legacy candidates to public signals.
    shadow={"legacy_eligible":0,"strict_eligible":0,"legacy_only":0,"strict_only":0,"neither":0,"compared":0}
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
                signal=scan_bars(ticker,bars,now.date(),liquidity_floor=0)
                legacy=scan_bars(ticker,bars,now.date(),strict_quality=False)
                shadow["compared"]+=1
                shadow["legacy_eligible"]+=int(legacy is not None)
                shadow["strict_eligible"]+=int(signal is not None)
                shadow["legacy_only"]+=int(legacy is not None and signal is None)
                shadow["strict_only"]+=int(signal is not None and legacy is None)
                shadow["neither"]+=int(legacy is None and signal is None)
                if legacy is not None:
                    shadow_cases.append(quality_shadow_record(legacy,signal))
                if signal:
                    # Only after structural screening: avoid per-ticker metadata calls
                    # for the entire rotating universe. Quote currency must come from
                    # the provider, not ticker suffix or a guessed exchange.
                    currency_checked+=1
                    try:
                        currency=yf.Ticker(ticker).fast_info.get("currency")
                    except (AttributeError,KeyError,TypeError,ValueError):
                        currency=None
                    diagnostics=signal["quantitativeDiagnostics"]
                    local_turnover=diagnostics.get("averageDollarVolume20")
                    usd_turnover=verified_usd_liquidity(local_turnover,currency,fx,now.date())
                    if usd_turnover is None or usd_turnover<5_000_000:
                        currency_rejected+=1
                        continue
                    diagnostics["averageLocalTurnover20"]=local_turnover
                    diagnostics["quoteCurrency"]=currency
                    diagnostics["averageDollarVolume20"]=round(usd_turnover,2)
                    diagnostics["liquidityFxReferenceDate"]=fx["ecb_reference_date"]
                    diagnostics["liquidityCurrencySource"]="yahoo_fast_info"
                    found.append(signal)
            except (KeyError,ValueError,TypeError) as exc:failures.append(f"{ticker}:{type(exc).__name__}")
    # Do not retain previously accepted setups after the stricter criteria reject them.
    by={signal["ticker"]:signal for signal in found}
    published,focus=published_signals_with_focus(list(by.values()),now.date())
    payload={"schema":"vestra_prebreakout_v1","generated_at":now.isoformat(),
             "attempted":len(tickers),"with_ohlcv":checked,"eligible_universe":eligible,"coverage_this_slot":round(checked/eligible,4) if eligible else None,"coverage_scope":"single_scan_slot_not_full_universe","new_signals":len(found),"liquidity_currency_checked":currency_checked,"liquidity_currency_rejected":currency_rejected,"quality_model":"vcp_before_pivot_v3","scan_slot_utc":now.hour//6,
             "errors":failures[:8],"quality_filter_shadow":{"method":"same_bars_current_slot_counterfactual_not_historical_backtest","not_probability":True,**shadow},
             "quality_shadow_cases":{"purpose":"prospective_same_slot_comparison_not_dashboard_candidates",
                  "outcomes_available":False,"records":sorted(shadow_cases,key=lambda x:(x["ticker"],x["date"]))},
             "daily_focus":focus,"signals":published}
    OUTPUT.write_text(json.dumps(payload,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in payload.items() if k!="signals"}))

if __name__=="__main__":main()
