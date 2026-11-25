#!/usr/bin/env python3
"""Bounded daily pre-breakout scan: verified Yahoo OHLCV, never an entry recommendation."""
from __future__ import annotations
import json
import hashlib
import math
import time
from datetime import datetime, timezone, date
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
INDEX=ROOT/"data"/"stocks-index.json"
OUTPUT=ROOT/"data"/"prebreakout-signals.json"
SCAN_BUDGET_PER_SLOT=400
SCANNER_SLOTS_PER_DAY=4
MAX_ADAPTIVE_SCAN_BUDGET_PER_SLOT=500
MAX_WATCH_RECHECKS=25


def slot_scan_budget(eligible: int) -> int:
    """Bounded uplift when four fixed slots cannot cover the eligible universe.

    Reserve capacity for repeated historical watch names without crowding out
    distinct OHLCV observations. Requests are not proof of successful coverage.
    """
    if type(eligible) is not int or eligible < 0:
        raise ValueError("eligible universe must be a nonnegative integer")
    if eligible <= SCAN_BUDGET_PER_SLOT * SCANNER_SLOTS_PER_DAY:
        return SCAN_BUDGET_PER_SLOT
    needed=math.ceil(eligible / SCANNER_SLOTS_PER_DAY) + MAX_WATCH_RECHECKS
    return min(MAX_ADAPTIVE_SCAN_BUDGET_PER_SLOT,needed)

def daily_coverage_capacity(eligible: int)->dict:
    """Honest upper bound, not observed coverage or a performance promise."""
    if type(eligible) is not int or eligible<0:
        raise ValueError("eligible universe must be a nonnegative integer")
    budget=slot_scan_budget(eligible)
    # Above the 1,600-name baseline the adaptive plan intentionally reserves
    # up to 25 recurring watched names on EACH slot. Count the reservation
    # once across the day, not four times as if all rechecks were new.
    reserved=min(MAX_WATCH_RECHECKS,eligible) if eligible>SCAN_BUDGET_PER_SLOT*SCANNER_SLOTS_PER_DAY else 0
    distinct=min(eligible, reserved+(budget-reserved)*SCANNER_SLOTS_PER_DAY)
    return {"max_distinct_daily":distinct,
            "requests_per_slot":budget,
            "maximum_requests_per_slot":MAX_ADAPTIVE_SCAN_BUDGET_PER_SLOT,
            "max_daily_coverage_pct":round(100*distinct/eligible,2) if eligible else None,
            "assumes":("four_slots_all_complete_disjoint_except_25_reserved_watch_rechecks"
                       if reserved else "four_slots_all_complete_disjoint_no_watchlist_overrides"),
            "watchlist_recheck_reservation_per_slot":reserved,
            "planning_capacity_not_verified_ohlcv":True,
            "not_actual_coverage":True}


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

def swing_contraction_shadow(bars: list[dict], *, lookback: int=120, radius: int=3)->dict:
    """Research-only VCP geometry from completed local price swings.

    This is deliberately NOT an eligibility gate: extrema need `radius`
    subsequently observed bars and only use the closed history supplied at
    the evaluation timestamp. Three successive, non-overlapping pullbacks
    are necessary, but they cannot establish a tradable signal on their own.
    """
    if len(bars)<lookback or radius<2:
        return {"status":"insufficient_history","research_only":True}
    sample=bars[-lookback:]
    extremes=[]
    for i in range(radius,len(sample)-radius):
        prev=sample[i-radius:i]
        future=sample[i+1:i+1+radius]
        h=sample[i]["high"];l=sample[i]["low"]
        if h>max(x["high"] for x in prev) and h>=max(x["high"] for x in future):
            extremes.append((i,"peak",h))
        if l<min(x["low"] for x in prev) and l<=min(x["low"] for x in future):
            extremes.append((i,"trough",l))
    # Adjacent identical types are one extremum: keep the most extreme.
    alternating=[]
    for item in sorted(extremes,key=lambda x:(x[0],0 if x[1]=="peak" else 1)):
        if alternating and item[1]==alternating[-1][1]:
            last=alternating[-1]
            if (item[2]>last[2] if item[1]=="peak" else item[2]<last[2]):
                alternating[-1]=item
        else:
            alternating.append(item)
    legs=[]
    for peak,trough in zip(alternating,alternating[1:]):
        if peak[1]!="peak" or trough[1]!="trough":continue
        duration=trough[0]-peak[0]
        depth=(peak[2]/trough[2]-1)*100
        if 4<=duration<=45 and depth>=3:
            legs.append({"peak_index":peak[0],"trough_index":trough[0],
                         "depth_pct":round(depth,3),"duration_sessions":duration})
    latest=legs[-3:]
    depths=[leg["depth_pct"] for leg in latest]
    contracted=(len(depths)==3 and depths[0]>0 and
                depths[1]<=depths[0]*.85 and depths[2]<=depths[1]*.85)
    if latest:
        first=latest[0]["peak_index"]
        base=sample[first:]
        width=(max(x["high"] for x in base)/min(x["low"] for x in base)-1)*100
        resistance=max(x["high"] for x in base[:-1]) if len(base)>1 else None
    else:
        width=None;resistance=None
    close=sample[-1]["close"]
    distance=(resistance/close-1)*100 if resistance and close>0 else None
    near_pivot=(distance is not None and 0<=distance<=8 and
                sample[-1]["high"]<=resistance*1.005)
    narrow=(width is not None and width<=22)
    fresh_pullback=bool(latest and len(sample)-1-latest[-1]["trough_index"]<=25)
    return {"status":"measured","research_only":True,
            "method":"confirmed_radius3_local_extrema_last120_closed_bars",
            "leg_depths_pct":depths,"leg_durations_sessions":[x["duration_sessions"] for x in latest],
            "legs_found":len(legs),"base_width_pct":round(width,3) if width is not None else None,
            "distance_to_resistance_pct":round(distance,3) if distance is not None else None,
            "sequential_contraction_pass":bool(contracted),
            "base_width_pass":bool(narrow),"below_pivot_pass":bool(near_pivot),
            "latest_pullback_recent":fresh_pullback,
            "all_geometry_pass":bool(contracted and narrow and near_pivot and fresh_pullback),
            "not_a_signal_no_volume_liquidity_lineage_or_forward_validation":True}


def technical_evidence_shadow(bars: list[dict])->dict:
    """Point-in-time technical features even for a rejected price pattern.

    These quantities are descriptive, never a standalone score, eligibility
    override or historical prediction. Missing volumes remain missing.
    """
    if len(bars)<80:
        return {"status":"insufficient_history","research_only":True}
    sample=bars[-80:]
    closes=[b["close"] for b in sample]
    true_ranges=[max(sample[i]["high"]-sample[i]["low"],
                     abs(sample[i]["high"]-closes[i-1]),
                     abs(sample[i]["low"]-closes[i-1]))
                 for i in range(1,len(sample))]
    atr14=sum(true_ranges[-14:])/14
    atr60=sum(true_ranges[-60:])/60
    returns=[math.log(closes[i]/closes[i-1]) for i in range(1,len(closes))]
    def deviation(part):
        mean=sum(part)/len(part)
        return math.sqrt(sum((v-mean)**2 for v in part)/len(part))
    vol10=deviation(returns[-10:]);vol40=deviation(returns[-40:])
    volumes=[b.get("volume") for b in sample]
    volume_complete=all(type(v) in (int,float) and math.isfinite(v) and v>0 for v in volumes[-50:])
    volume_ratio=(sum(volumes[-10:-1])/9)/(sum(volumes[-50:-10])/40) if volume_complete else None
    closes20=closes[-21:]
    direction=abs(closes20[-1]-closes20[0])
    path=sum(abs(b-a) for a,b in zip(closes20,closes20[1:]))
    efficiency=direction/path if path>0 else None
    high20=max(b["high"] for b in sample[-20:]);low20=min(b["low"] for b in sample[-20:])
    return {"status":"measured","research_only":True,
            "atr14_pct":round(100*atr14/closes[-1],3),
            "atr14_to_atr60":round(atr14/atr60,3) if atr60>0 else None,
            "realized_vol10_to_vol40":round(vol10/vol40,3) if vol40>0 else None,
            "volume9_to_prior40":round(volume_ratio,3) if volume_ratio is not None else None,
            "return20_pct":round(100*(closes[-1]/closes[-21]-1),3),
            "return60_pct":round(100*(closes[-1]/closes[-61]-1),3),
            "efficiency20":round(efficiency,3) if efficiency is not None else None,
            "close_position20":round((closes[-1]-low20)/(high20-low20),3) if high20>low20 else None,
            "relative_strength_to_index":None,
            "missing_relative_strength_is_not_neutral_or_zero":True,
            "not_signal_or_backtest_or_calibrated_probability":True}


def scan_bars(ticker: str, bars: list[dict], today: date|None=None, *, strict_quality: bool=True, liquidity_floor: float=5_000_000, audit: dict|None=None):
    """Identify a contracting base, not a prediction of future returns."""
    def reject(reason: str):
        if audit is not None:
            audit['first_rejection'] = reason
        return None
    today=today or datetime.now(timezone.utc).date()
    # All eligibility gates use at most 252 closed sessions (MA200, VCP60,
    # historical pivot100 and high52). Older provider corruption must not
    # veto otherwise complete current evidence. Invalid bars *within* the
    # canonical window remain fatal; never drop or interpolate them.
    bars=bars[-252:]
    clean=[]
    for bar_index, bar in enumerate(bars):
        if not isinstance(bar, dict):
            if audit is not None: audit["invalid_ohlcv_detail"] = "non_mapping_bar"
            return reject("invalid_ohlcv_or_date")
        # Diagnose the first unusable bar only. Never repair missing prices,
        # drop invalid sessions or promote a ticker that fails this check.
        if any(isinstance(bar.get(field), bool) for field in ("close", "high", "low", "volume")):
            if audit is not None: audit["invalid_ohlcv_detail"] = "boolean_price_or_volume"
            return reject("invalid_ohlcv_or_date")
        try:
            day=date.fromisoformat(str(bar["date"])[:10])
        except (KeyError,ValueError,TypeError,OverflowError):
            if audit is not None: audit["invalid_ohlcv_detail"] = "invalid_or_missing_date"
            return reject("invalid_ohlcv_or_date")
        for field in ("close", "high", "low"):
            try:
                value=float(bar[field])
            except (KeyError,ValueError,TypeError,OverflowError):
                if audit is not None:
                    audit["invalid_ohlcv_detail"] = "invalid_or_missing_" + field
                    if field == "close":
                        # Distinguish provider outer-join padding from a genuine
                        # missing in-range close. Diagnostics only: no bars dropped.
                        audit["missing_close_bar_location"] = (
                            "leading" if bar_index == 0 else
                            "trailing" if bar_index == len(bars) - 1 else "interior"
                        )
                        if bar.get("close") is None:
                            if bar.get("high") is None and bar.get("low") is None:
                                audit["missing_close_pattern"] = "all_ohlc_missing"
                            elif bar.get("high") is not None and bar.get("low") is not None:
                                audit["missing_close_pattern"] = "close_only_missing"
                            else:
                                audit["missing_close_pattern"] = "partial_ohlc_missing"
                        else:
                            audit["missing_close_pattern"] = "invalid_nonnull_close"
                return reject("invalid_ohlcv_or_date")
            if not math.isfinite(value):
                if audit is not None:
                    audit["nonfinite_ohlc_detail"] = field
                return reject("nonfinite_ohlc")
            if field == "close": close=value
            elif field == "high": high=value
            else: low=value
        if not all(math.isfinite(v) for v in (close,high,low)):
            return reject('nonfinite_ohlc')
        if not (0<low<=close<=high):
            return reject('inconsistent_ohlc')
        if clean and day<=clean[-1]["day"]:
            return reject('duplicate_or_out_of_order_sessions')
        clean.append({**bar,"day":day,"close":close,"high":high,"low":low})
    if len(clean)<220:return reject('insufficient_daily_sessions')
    latest=clean[-1]["day"]
    age=(today-latest).days
    if not 0<=age<=7:return reject('stale_or_future_daily_session')
    def bounds(part):
        return max(b["high"] for b in part),min(b["low"] for b in part)
    def width(part):
        high,low=bounds(part)
        return high/low-1
    # Research-only independent geometry: a moving-average rejection must not
    # conceal whether a contracting price base exists in the same valid bars.
    prior=clean[-100:-60];first=clean[-60:-40];second=clean[-40:-20];third=clean[-20:]
    old_width=width(prior);w1=width(first);w2=width(second);w3=width(third)
    base_width=width(clean[-40:])
    base_width_ok=old_width>0 and base_width<=.22 and base_width<old_width*.8
    # A zero-width window is not measured volatility contraction: a
    # non-trading/frozen price cannot validate the second and third legs.
    # Require all three independent 20-session spans to have real range.
    vcp_ok=w1>0 and w2>0 and w3>0 and w2<=w1*.85 and w3<=w2*.85
    if audit is not None:
        audit["swing_geometry_shadow"]=swing_contraction_shadow(clean)
        audit["technical_evidence_shadow"]=technical_evidence_shadow(clean)
        # A research watch is displayed even when the main scan rejects on
        # moving averages. Independently verify that its base is still below
        # an unbroken pivot; never let a MA rejection hide an earlier breakout.
        prior_pivot=max(b["high"] for b in clean[-40:-1])
        last_bar=clean[-1]
        pivot_distance_pct=100*(prior_pivot/last_bar["close"]-1)
        confirmed_in_base=historical_breakout_dates(clean,len(clean)-39,len(clean)-1)
        # Freeze the exact as-of reference used by the observation. Later
        # Yahoo auto-adjustments can revise prices; the archived pivot/close
        # are original observed evidence, not a reconstructed price factor.
        # This never overrides a gate or certifies future price comparability.
        base_bars=clean[-40:]
        compact_bars=[
            [b["day"].isoformat(),b["close"],b["high"],b["low"],
             float(b["volume"]) if type(b.get("volume")) in (int,float)
                 and math.isfinite(b["volume"]) else None]
            for b in base_bars]
        audit["asof_base_price_anchor"]={
            "schema":"vestra_prebreakout_asof_base_anchor_v1",
            "session":last_bar["day"].isoformat(),
            "base_start_session":base_bars[0]["day"].isoformat(),
            "reference_bars":39,
            "window_bars":40,
            "adjusted_close":last_bar["close"],
            "adjusted_pivot_high":prior_pivot,
            "observed_last_high":last_bar["high"],
            "basis":"yahoo_auto_adjusted_daily_ohlcv_at_capture",
            "closed_bar_snapshot_sha256":hashlib.sha256(
                json.dumps(compact_bars,separators=(",",":"),allow_nan=False)
                .encode("utf-8")).hexdigest(),
            "historical_adjustment_factor_verified":False,
            "research_only_no_eligibility_or_score_effect":True}
        audit["research_prebreakout_lineage"]={
            "distance_to_pivot_pct":round(pivot_distance_pct,3),
            "prior_confirmed_breakouts_in_base":len(confirmed_in_base),
            "unbroken_prebreakout_position":(
                0<=pivot_distance_pct<=8 and
                last_bar["high"]<=prior_pivot*1.005 and
                not confirmed_in_base),
            "research_only_no_eligibility_or_score_effect":True}
        # The canonical signal remains end-anchored. This separate research
        # measurement asks whether the same fixed-window geometry survives a
        # change of window phase by up to ten historical sessions. A pattern
        # that passes only one phase is fragile; extra phase passes NEVER
        # turn a failed canonical signal into a candidate.
        phase_passes=[]
        for lag in range(11):
            sample=clean if lag==0 else clean[:-lag]
            prior_phase=width(sample[-100:-60])
            phase_base=width(sample[-40:])
            phase_w1=width(sample[-60:-40])
            phase_w2=width(sample[-40:-20])
            phase_w3=width(sample[-20:])
            phase_base_ok=(prior_phase>0 and phase_base<=.22
                           and phase_base<prior_phase*.8)
            phase_vcp_ok=(phase_w1>0 and phase_w2>0 and phase_w3>0
                          and phase_w2<=phase_w1*.85
                          and phase_w3<=phase_w2*.85)
            phase_passes.append((phase_base_ok,phase_vcp_ok))
        audit["geometry_phase_shadow"]={
            "phase_offsets_sessions":list(range(11)),
            "base_width_pass_count":sum(a for a,_ in phase_passes),
            "contractions_pass_count":sum(b for _,b in phase_passes),
            "both_pass_count":sum(a and b for a,b in phase_passes),
            "canonical_both_pass":base_width_ok and vcp_ok,
            "research_only_no_eligibility_or_score_effect":True}
        audit["geometry_shadow"]={"base_width_pass":bool(base_width_ok),
                                  "contractions_pass":bool(vcp_ok),
                                  "both_pass":bool(base_width_ok and vcp_ok),
                                  # Raw observed geometry, in percentage points.
                                  # Supports threshold-distance audits without
                                  # altering the canonical eligibility rules.
                                  "prior_width_pct":round(old_width*100,3),
                                  "base_width_pct":round(base_width*100,3),
                                  "w1_pct":round(w1*100,3),
                                  "w2_pct":round(w2*100,3),
                                  "w3_pct":round(w3*100,3),
                                  "all_contraction_windows_nonflat":bool(w1>0 and w2>0 and w3>0),
                                  "research_only_not_eligibility":True}
    end=len(clean)-1
    values=[b["close"] for b in clean]
    m50=sma(values,end,50);m150=sma(values,end,150);m200=sma(values,end,200)
    slopes=[m50-sma(values,end-10,50),m150-sma(values,end-10,150),m200-sma(values,end-10,200)]
    ma_structure=(values[-1]>m50>m150>m200 if strict_quality else values[-1]>m150 and m50>m200)
    if audit is not None:
        # Measure MA and base geometry on the same observed bars, independently
        # of which gate happens to fail first. This is descriptive only.
        audit["ma_structure_shadow"]={
            "status":"measured",
            "price_order_pass":bool(ma_structure),
            "three_slopes_rising":bool(all(x>0 for x in slopes)),
            "all_pass":bool(ma_structure and all(x>0 for x in slopes)),
            "research_only_no_eligibility_or_score_effect":True}
    if not (ma_structure and all(x>0 for x in slopes)):
        # Research-only: report *overlapping* reasons for this first failing gate.
        # Do not turn these diagnostics into relaxed eligibility or a prediction.
        if audit is not None:
            checks=({"price_above_ma50":values[-1]>m50,
                     "ma50_above_ma150":m50>m150,
                     "ma150_above_ma200":m150>m200} if strict_quality else
                    {"price_above_ma150":values[-1]>m150,
                     "ma50_above_ma200":m50>m200})
            checks.update({"ma50_rising_10":slopes[0]>0,
                           "ma150_rising_10":slopes[1]>0,
                           "ma200_rising_10":slopes[2]>0})
            audit["moving_average_failed_checks"]=sorted(k for k,ok in checks.items() if not ok)
        return reject('moving_average_structure')
    # Require sequential, non-overlapping contractions, not merely one quieter 40-day window.
    if not base_width_ok:
        return reject('base_width')
    if not vcp_ok:return reject('sequential_vcp_contractions')
    resistance=bounds(clean[-40:-1])[0]
    current=values[-1]
    distance=(resistance/current-1)*100
    if distance>8 or distance<0:return reject('distance_to_pivot')  # PRE-breakout only: last close must remain at/below pivot.
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
    if breakout or clean[-1]["high"]>resistance*1.005:return reject('already_broken_pivot')
    # A new signal cannot reuse a base after a confirmed breakout inside its 40-bar window.
    # Older confirmed events are reported as lineage context, not as fresh entry signals.
    if historical_breakout_dates(clean, len(clean)-39, len(clean)-1):
        return reject('prior_confirmed_breakout_in_base')
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
        return reject('local_liquidity_or_base_position')
    # A tight 40-session pause after a major earlier rally is a continuation
    # base, not an early breakout opportunity. Use only closes strictly before
    # the current base, with a robust 15th-percentile reference (not a wick).
    prior_closes=sorted(b['close'] for b in clean[-160:-40])
    prior_reference=prior_closes[int((len(prior_closes)-1)*.15)]
    prior_impulse_pct=(clean[-40]['close']/prior_reference-1)*100
    # Price-only run-up and separately verified historical volume breakouts are
    # complementary lineage evidence. A breakout anywhere in the 180 sessions
    # preceding the current base means this is NOT the initial opportunity.
    prior_confirmed=historical_breakout_dates(clean,len(clean)-180,len(clean)-40)
    phase=('continuation_after_prior_impulse' if prior_impulse_pct>=25 else
           'continuation_after_confirmed_breakout' if prior_confirmed else
           'initial_base_not_extended')
    if audit is not None:
        audit['trend_phase']={'classification':phase,
            'prebase_impulse_pct':round(prior_impulse_pct,2),
            'lookback_sessions':120,'reference':'prior_15th_percentile_adjusted_close',
            'previous_confirmed_breakout_date':prior_confirmed[-1] if prior_confirmed else None,
            'no_future_sessions':True}
    if strict_quality and phase!='initial_base_not_extended':
        return reject('prior_impulse_continuation')
    # The last 10 sessions should not repeatedly close in the weak lower
    # half of the base. Use closed bars only, no forward/market data.
    midpoint=(base_high+base_low)/2
    upper_half_closes=sum(b["close"]>=midpoint for b in clean[-10:])
    support_retention=round(upper_half_closes/10,2)
    # Closed-session high across 252 bars: research diagnostic, not a gate or score.
    high52=max(bar["high"] for bar in clean[-252:]) if len(clean)>=252 else None
    high52_proximity=round(current/high52*100,2) if high52 is not None and high52>0 else None
    # Research-only impulse context: distinguish base geometry from a sharp prior rally.
    # Fixed closed-bar windows, no new provider calls or live eligibility changes.
    prebase_return_pct=(clean[-40]["close"]/clean[-80]["close"]-1)*100
    prebase_range_pct=width(clean[-80:-40])*100
    diagnostics={"preBaseReturn40Pct":round(prebase_return_pct,2),
                 "preBaseRange40Pct":round(prebase_range_pct,2),
                 "contractionWidths20Pct":[round(w*100,2) for w in (w1,w2,w3)],
                 "preBaseContext":"research_only_fixed_closed_bars_no_ranking_gate",
                 "high52Week":round(high52,5) if high52 is not None else None,
                 "closeToHigh52WeekPct":high52_proximity,
                 "high52WeekWindowSessions":252 if high52 is not None else None,
                 "high52WeekBasis":"last_252_closed_ohlcv_bars_asof_signal",
                 "baseUpperHalfCloses10":upper_half_closes,"baseSupportRetention10":support_retention,"atrPct14":round(atr14/current*100,3),"atrContractionRatio":round(atr14/atr60,3) if atr60>0 else None,
                 "averageDollarVolume20":round(dollar_volume20,2) if dollar_volume20 is not None else None,"basePositionPct":round(base_position*100,1),
                 "qualityGates":(["sma50_gt_sma150_gt_sma200","price_above_sma50","dollar_volume20_gte_5m","base_position_gte_65pct"] if strict_quality else [])}
    if audit is not None:
        audit['first_rejection'] = 'passed_structural_gates'
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

def earnings_risk_from_latest(path:Path, as_of:date, tickers:list[str])->dict:
    """Conservative research pick embargo: missing future dates are unknown.
    The 17-day calendar buffer intentionally overcovers 10 US market sessions;
    it is not an exact exchange-session count.
    """
    out={t:{'status':'unknown','next_date':None} for t in tickers}
    try:
        feed=json.loads(path.read_text(encoding="utf-8"))
        stamp=datetime.fromisoformat(str(feed["generated_at"]).replace("Z","+00:00"))
        if stamp.tzinfo is None or feed.get("schema")!="vestra_earnings_latest_v1" or not isinstance(feed.get("stocks"),list): return out
        if not 0<=(as_of-stamp.date()).days<=2: return out
    except (OSError,ValueError,TypeError,KeyError,AttributeError): return out
    for row in feed['stocks']:
        if not isinstance(row,dict) or row.get('ticker') not in out: continue
        try: day=date.fromisoformat(str(row['analyst_next_earnings_date'])[:10])
        except (KeyError,ValueError,TypeError): continue
        if day<as_of: continue
        out[row['ticker']]={'status':'near_term' if (day-as_of).days<=17 else 'dated_beyond_buffer',
            'next_date':day.isoformat(),'method':'conservative_17_calendar_day_proxy'}
    return out

def daily_focus(signals:list[dict], as_of:date, earnings_risks:dict|None=None)->dict:
    """One evidence-led candidate, or an explicit abstention; never a success probability."""
    eligible=[]
    developing=[]
    for row in signals:
        if earnings_risks is not None and earnings_risks.get(row.get("ticker"),{}).get("status")!="dated_beyond_buffer": continue
        if row.get("stage") not in ("pré-breakout","compressão") or row.get("source")!="yahoo:daily_ohlcv":
            continue
        if row.get("vcpConfirmed") is not True:
            continue
        if row.get("volumeConfirmed") is True:
            continue  # This slot is for setups still awaiting a breakout.
        try:
            day=date.fromisoformat(str(row["date"])[:10])
            distance=float(row["distancePct"])
            score=float(row["score"])
        except (KeyError,ValueError,TypeError):
            continue
        if not (0 <= (as_of-day).days <= 4 and math.isfinite(distance) and 0<=distance<=8 and math.isfinite(score) and 0<=score<=100):
            continue
        if row.get("stage")=="pré-breakout" and row.get("volumeDry") is True and distance<=4:
            eligible.append(row)
        else:
            developing.append(row)
    if not eligible and not developing:
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
    fallback=not eligible
    best=min(eligible if eligible else developing,key=focus_rank)
    shadow=structural_readiness_shadow(best)
    return {"structural_readiness_shadow":shadow,
            "status":"research_candidate","ticker":best["ticker"],
            "signal_date":best["date"],"stage":best["stage"],
            "technical_score":best["score"],"distance_to_pivot_pct":best["distancePct"],
            "success_probability":None,"probability_calibrated":False,
            "selection_tier":"developing_setup" if fallback else "verified_prebreakout",
            "reason":"best_available_developing_base_not_confirmed" if fallback else "ranked_verified_setup_not_a_forecast_or_buy_signal"}

def published_signals_with_focus(signals:list[dict],as_of:date,limit:int=75,earnings_risks:dict|None=None)->tuple[list[dict],dict]:
    """Keep the featured candidate in the public list even when capped."""
    if limit<1:
        raise ValueError("published signal limit must be positive")
    ordered=sorted(signals,key=lambda row:({"pré-breakout":0,"compressão":1}[row["stage"]],-row["score"],row["ticker"]))
    focus=daily_focus(ordered,as_of,earnings_risks)
    visible=ordered[:limit]
    if focus["status"]=="research_candidate" and all(row["ticker"]!=focus["ticker"] for row in visible):
        featured=next(row for row in ordered if row["ticker"]==focus["ticker"])
        visible=sorted(visible[:-1]+[featured],
                       key=lambda row:({"pré-breakout":0,"compressão":1}[row["stage"]],-row["score"],row["ticker"]))
    return visible,focus

def structural_readiness_shadow(signal:dict|None)->dict:
    """As-of research-only classification. Never change live signals or forecast odds."""
    q=signal.get("quantitativeDiagnostics") if isinstance(signal,dict) else None
    if not isinstance(q,dict):
        return {"model":"atr_support_v1_shadow","status":"unverifiable","eligible":None}
    observed=[]
    for key in ("atrContractionRatio","baseSupportRetention10","basePositionPct"):
        value=q.get(key)
        if type(value) not in (float,int) or not math.isfinite(value):
            return {"model":"atr_support_v1_shadow","status":"unverifiable","eligible":None}
        observed.append(float(value))
    atr,support,position=observed
    if not (0<atr<=5 and 0<=support<=1 and 0<=position<=100):
        return {"model":"atr_support_v1_shadow","status":"unverifiable","eligible":None}
    eligible=atr<=.8 and support>=.8 and position>=80
    return {"model":"atr_support_v1_shadow",
            "status":"research_eligible" if eligible else "research_rejected",
            "eligible":eligible}


def quality_shadow_record(legacy:dict, strict:dict|None)->dict:
    """Research-only point-in-time evidence; never a public recommendation."""
    return {"ticker":legacy["ticker"],"date":legacy["date"],"stage":legacy["stage"],
            "baseStartDate":legacy.get("baseStartDate"),
            "previousConfirmedBreakoutDate":legacy.get("previousConfirmedBreakoutDate"),
            "resistance":legacy["resistance"],"signalClose":legacy["signalClose"],
            "signalPriceBasis":legacy.get("signalPriceBasis"),
            "legacy_eligible":True,"strict_eligible":strict is not None,
            "structural_readiness_shadow":structural_readiness_shadow(strict),
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

def eligible_universe_tickers(stocks: list[dict])->set[str]:
    tickers=set()
    for stock in stocks:
        ticker=str(stock.get("ticker") or "").strip().upper()
        qt=str(stock.get("quote_type") or "").upper()
        cap=stock.get("market_cap")
        if ticker and qt not in ("ETF","FUND","MUTUALFUND","CRYPTO") and isinstance(cap,(int,float)) and math.isfinite(cap) and cap>=500_000_000:
            tickers.add(ticker)
    return tickers

def universe_provenance_audit(stocks:list[dict], previous:dict, index_bytes:bytes)->dict:
    """Fingerprint the actual eligibility denominator, not forecast coverage."""
    names=sorted(eligible_universe_tickers(stocks))
    current=hashlib.sha256("\n".join(names).encode("utf-8")).hexdigest()
    prior_hash=previous.get("universe_provenance_audit",{}).get("eligible_tickers_sha256") if isinstance(previous.get("universe_provenance_audit"),dict) else None
    prior_count=previous.get("eligible_universe")
    prior_valid=isinstance(prior_hash,str) and len(prior_hash)==64 and all(ch in "0123456789abcdef" for ch in prior_hash)
    count_valid=type(prior_count) is int and prior_count>=0
    return {"source_index_sha256":hashlib.sha256(index_bytes).hexdigest(),
            "eligible_tickers_sha256":current,
            "eligible_count":len(names),
            "previous_eligible_count":prior_count if count_valid else None,
            "eligible_count_change":len(names)-prior_count if count_valid else None,
            "membership_changed":current!=prior_hash if prior_valid else None,
            "membership_comparison":"same_identity_fingerprint_or_changed" if prior_valid else "unknown_prior_fingerprint",
            "source_snapshot_comparison":"fingerprint_only_not_member_level_diff",
            "coverage_is_not_signal_performance":True}

def eligible_universe_size(stocks: list[dict])->int:
    return len(eligible_universe_tickers(stocks))

def candidates(stocks: list[dict], when: date, slot: int = 0, watch: list[str]|None=None, *, recently_verified:set[str]|None=None):
    universe={}
    for s in stocks:
        ticker=str(s.get("ticker") or "").strip().upper()
        qt=str(s.get("quote_type") or "").upper()
        cap=s.get("market_cap")
        if not ticker or qt in ("ETF","FUND","MUTUALFUND","CRYPTO") or not isinstance(cap,(int,float)) or not math.isfinite(cap) or cap<500_000_000:
            continue
        universe[ticker]=max(cap,universe.get(ticker,0))
    ordered=sorted(universe,key=lambda t:(-universe[t],t))
    # Four daily slots use a bounded adaptive budget for universes >1,600;\n    # planned requests are not proof of downloaded/evaluable OHLCV.\n    # A daily-bar scanner gains no fresh evidence by rereading fixed anchors
    # on all four slots. Rotate the complete eligible universe instead.
    if not 0<=slot<=3:raise ValueError("invalid six-hour scan slot")
    if not ordered:return []
    budget=slot_scan_budget(len(ordered))
    watchlist=[]
    for ticker in watch or []:
        if ticker in universe and ticker not in watchlist:
            watchlist.append(ticker)
            if len(watchlist)>=MAX_WATCH_RECHECKS:break
    # Adaptive rotation must operate over the NON-WATCH population.
    # Rotating the full population and only THEN removing watchlist names
    # reintroduces overlap across adjacent slots when watch names fall within
    # the rotated segment. Legacy <=1,600 behavior remains unchanged.
    adaptive=budget>SCAN_BUDGET_PER_SLOT
    rotation_universe=([t for t in ordered if t not in watchlist]
                       if adaptive else ordered)
    stride=(budget-len(watchlist) if adaptive else SCAN_BUDGET_PER_SLOT)
    offset=(((when-date(2026,10,13)).days*4+slot)*stride)%len(rotation_universe)
    rotated=rotation_universe[offset:]+rotation_universe[:offset]
    # Historical watch candidates are rechecked, never promoted from cache.
    rotation=(rotated if adaptive else [t for t in rotated if t not in watchlist])
    if recently_verified is not None:
        # Daily OHLCV rarely changes between six-hour slots. When the
        # universe/capitalisation order moves, prioritize names not yet
        # verified in the last 24h; preserve the watchlist reservation.
        unseen=[t for t in rotation if t not in recently_verified]
        repeats=[t for t in rotation if t in recently_verified]
        rotation=unseen+repeats
    return watchlist+rotation[:budget-len(watchlist)]

def rotation_plan_audit(stocks:list[dict], when:date, watch:list[str]|None=None)->dict:
    """Deterministic four-slot selection plan, not proof any prices were downloaded."""
    slots=[candidates(stocks,when,slot,watch) for slot in range(SCANNER_SLOTS_PER_DAY)]
    flattened=[name for slot in slots for name in slot]
    distinct=len(set(flattened))
    eligible=eligible_universe_size(stocks)
    return {"status":"planned_not_observed","date":when.isoformat(),
            "planned_requests":len(flattened),"planned_distinct":distinct,
            "planned_repeats":len(flattened)-distinct,
            "planned_distinct_pct":round(100*distinct/eligible,2) if eligible else None,
            "eligible_universe":eligible,
            "not_actual_ohlcv_coverage":True}


def dataframe_bars(frame):
    rows=[]
    if frame is None or getattr(frame,"empty",True):return rows
    for idx,r in frame.iterrows():
        try:
            dt=idx.date().isoformat() if hasattr(idx,"date") else str(idx)[:10]
            # Keep invalid closes as explicit gaps: dropping a daily row
            # would silently compress 20/50/200-session evidence windows.
            def val(key):
                try:
                    raw=r[key]
                    # Python and NumPy Boolean data are not market prices or volume.
                    if isinstance(raw,bool) or (type(raw).__module__.startswith("numpy") and type(raw).__name__ in ("bool", "bool_")):
                        return None
                    n=float(raw)
                    return n if math.isfinite(n) else None
                except (KeyError,TypeError,ValueError,OverflowError):return None
            rows.append({"date":dt,"close":val("Close"),"high":val("High"),"low":val("Low"),"volume":val("Volume")})
        except (KeyError,ValueError,TypeError):continue
    return rows


def single_ticker_ohlcv_frame(data, ticker):
    """Extract a single ticker from either Yahoo download column layout.

    yfinance may retain MultiIndex columns for a one-symbol list download.
    Never interpret a different ticker's columns as the requested series.
    """
    columns = getattr(data, "columns", None)
    if getattr(columns, "nlevels", 1) <= 1:
        return data
    for level in range(columns.nlevels):
        if ticker in columns.get_level_values(level):
            return data.xs(ticker, axis=1, level=level)
    raise KeyError("ticker_missing_from_ohlcv_columns:" + ticker)

def completed_sessions(bars, utc_today):
    """Only completed UTC daily sessions are eligible for a verified stage."""
    return [bar for bar in bars if str(bar.get("date") or "")[:10] < utc_today.isoformat()]

def trim_leading_provider_padding(bars):
    """Remove only empty leading dates from a multi-ticker outer join.

    Yahoo's shared batch date index can predate an individual listing. Empty
    prefix rows are NOT observed trading sessions. Missing interior/trailing
    prices and partly populated OHLCV rows stay untouched and fail closed.
    """
    first = 0
    while first < len(bars):
        bar = bars[first]
        if not isinstance(bar, dict) or not isinstance(bar.get("date"), str):
            break
        try:
            date.fromisoformat(bar["date"][:10])
        except ValueError:
            break
        if not all(key in bar and bar[key] is None
                   for key in ("close", "high", "low", "volume")):
            break
        first += 1
    return bars[first:], first

def trim_trailing_provider_padding(bars):
    """Remove only fully null terminal dates from batch outer-join alignment.

    Yahoo sometimes encodes an outer-join placeholder as OHLC=None and
    Volume=0. That is not a zero-volume *trading* session because no price
    exists. Require a preceding observed bar; interior/partial rows remain
    fatal, and freshness is still checked against the last real session.
    """
    last=len(bars)
    while last>0:
        bar=bars[last-1]
        if not isinstance(bar,dict) or not isinstance(bar.get("date"),str):
            break
        try: date.fromisoformat(bar["date"][:10])
        except ValueError: break
        volume=bar.get("volume")
        if not (all(key in bar and bar[key] is None
                    for key in ("close","high","low"))
                and "volume" in bar
                and (volume is None or type(volume) in (int,float) and volume==0)):
            break
        last-=1
    # Do not manufacture a valid empty history from provider-wide failure.
    if last==0:return bars,0
    return bars[:last],len(bars)-last


def interior_all_null_gap_diagnostic(bars):
    """Describe fully absent interior OHLCV dates without changing price evidence.

    A multi-market Yahoo outer join may create empty dates for assets whose
    exchange was closed, but identical gaps may be provider failures. Neither
    interpretation is assumed: no rows are removed, repaired, or imputed.
    """
    required = ("close", "high", "low", "volume")
    def observed(row):
        return isinstance(row, dict) and any(row.get(k) is not None for k in required)
    def empty(row):
        return (isinstance(row, dict) and
                all(k in row and row[k] is None for k in required))
    anchors = [i for i, row in enumerate(bars) if observed(row)]
    result = {"gap_runs": 0, "gap_rows": 0, "single_day_runs": 0,
              "multi_day_runs": 0, "max_run_rows": 0,
              "weekday_rows": 0, "weekend_rows": 0,
              "invalid_date_rows": 0}
    if len(anchors) < 2:
        return result
    i = anchors[0] + 1
    while i < anchors[-1]:
        if not empty(bars[i]):
            i += 1
            continue
        j = i
        while j < anchors[-1] and empty(bars[j]):
            j += 1
        span = j - i
        result["gap_runs"] += 1
        result["gap_rows"] += span
        result["single_day_runs" if span == 1 else "multi_day_runs"] += 1
        result["max_run_rows"] = max(result["max_run_rows"], span)
        for row in bars[i:j]:
            try:
                day = date.fromisoformat(str(row["date"]))
                result["weekend_rows" if day.weekday() >= 5 else "weekday_rows"] += 1
            except (KeyError, ValueError, TypeError):
                result["invalid_date_rows"] += 1
        i = j
    return result



def verified_standalone_recovery(batch_bars, standalone_bars, today, audit=None):
    """Accept a separately fetched complete series only after cross-source consistency.

    Fully empty batch join rows are not evidence of trades; partial rows and
    contradictory overlapping observed OHLCV remain hard rejection conditions.
    No interpolation, forward fill or synthetic trading date is permitted.
    """
    def reject(reason):
        if audit is not None:
            audit["rejection_reason"] = reason
        return None

    if not evaluable_recheck(standalone_bars, today):
        return reject("independent_history_not_evaluable")
    # A positive-volume batch placeholder without ANY OHLC price is ambiguous.
    # It may be skipped only at the terminal boundary, and only if the
    # separately fetched valid series has no session on that date. Never
    # discard a priced bar or an interior / partially priced observation.
    standalone_dates={str(bar.get("date") or "")[:10] for bar in standalone_bars}
    terminal_unpriced=set()
    for bar in reversed(batch_bars):
        if not isinstance(bar,dict):break
        if not all(bar.get(key) is None for key in ("close","high","low")):
            break
        day=str(bar.get("date") or "")[:10]
        try:date.fromisoformat(day)
        except (ValueError,TypeError):break
        if day in standalone_dates:
            return reject("terminal_missing_price_conflicts_with_independent_session")
        terminal_unpriced.add(day)
    observed = {}
    for bar in batch_bars:
        if not isinstance(bar, dict):
            return reject("batch_non_mapping_bar")
        fields = (bar.get("close"), bar.get("high"), bar.get("low"), bar.get("volume"))
        if all(v is None for v in fields):
            continue
        if (str(bar.get("date") or "")[:10] in terminal_unpriced
                and all(v is None for v in fields[:3])
                and not isinstance(fields[3],bool)
                and (fields[3] is None or type(fields[3]) in (int,float)
                     and math.isfinite(fields[3]) and fields[3]>=0)):
            continue
        if any(v is None or isinstance(v, bool) for v in fields):
            return reject("batch_partial_or_boolean_bar")
        key = str(bar.get("date") or "")[:10]
        if not key or key in observed:
            return reject("batch_missing_or_duplicate_date")
        observed[key] = bar
    independent = {bar["date"][:10]: bar for bar in standalone_bars}
    common = set(observed) & set(independent)
    if not common or common != set(observed):
        return reject("independent_history_missing_observed_overlap")
    for key in common:
        for field in ("close", "high", "low", "volume"):
            a, b = float(observed[key][field]), float(independent[key][field])
            if not math.isfinite(a) or not math.isfinite(b):
                return reject("nonfinite_overlap")
            if abs(a-b)>max(1e-6, 1e-4*max(abs(a),abs(b))):
                return reject("conflicting_observed_ohlcv")
    if audit is not None:
        audit["verified"] = True
        audit["verified_terminal_unpriced_rows"] = len(terminal_unpriced)
    return standalone_bars


def evaluable_recheck(bars, today):
    """Only a complete, fresh, ordered OHLCV series can invalidate a prior setup."""
    bars=bars[-252:]
    if len(bars)<220:
        return False
    previous=None
    for bar in bars:
        if not isinstance(bar,dict) or any(isinstance(bar.get(k),bool) for k in ("close","high","low","volume")):
            return False
        try:
            day=date.fromisoformat(str(bar["date"])[:10])
            close=float(bar["close"]); high=float(bar["high"]); low=float(bar["low"])
            volume=float(bar["volume"])
        except (KeyError,ValueError,TypeError,OverflowError):
            return False
        if (previous is not None and day<=previous) or not all(map(math.isfinite,(close,high,low,volume))):
            return False
        if not (0<low<=close<=high and volume>=0):
            return False
        previous=day
    return 0 <= (today-previous).days <= 7

def verified_usd_liquidity(local_turnover, currency, fx, today):
    """Normalize quoted cash turnover to USD; unresolved units/rates fail closed."""
    if isinstance(local_turnover,bool) or not isinstance(local_turnover,(int,float)) or not math.isfinite(local_turnover) or local_turnover<=0:
        return None
    if not isinstance(currency,str) or not currency.strip():
        return None
    unit=currency.strip()
    currency_code="GBP" if unit in ("GBP","GBp","GBX") else unit.upper()
    factor=.01 if unit in ("GBp","GBX") else 1.0
    try:
        reference=date.fromisoformat(str(fx["ecb_reference_date"])[:10])
        rates=fx["rates_to_eur"]
        # Boolean exchange rates are not observed FX evidence.
        if any(isinstance(rates[code],bool) for code in (currency_code,"USD")):
            return None
        local=float(rates[currency_code]);usd=float(rates["USD"])
    except (KeyError,ValueError,TypeError,OverflowError):
        return None
    if not 0 <= (today-reference).days <= 7 or not all(math.isfinite(x) and x>0 for x in (local,usd)):
        return None
    return local_turnover*factor*local/usd

EARLY_SETUP_POLICY_VERSION = "initial_base_lineage_v2"


def recent_verified_signals(previous:dict, scanned_tickers:list[str], now:datetime)->list[dict]:
    """Carry forward only per-ticker recently verified candidates, never stale/rechecked rows."""
    if (previous.get("schema")!="vestra_prebreakout_v1" or
        previous.get("quality_model")!="vcp_before_pivot_v3" or
        previous.get("early_setup_policy_version")!=EARLY_SETUP_POLICY_VERSION):
        return []
    try:
        generated=datetime.fromisoformat(previous["generated_at"].replace("Z","+00:00"))
        if generated.tzinfo is None or not 0 <= (now-generated).total_seconds() <= 18*3600:
            return []
    except (KeyError,AttributeError,TypeError,ValueError):
        return []
    observed=set(scanned_tickers)
    retained=[]
    for row in previous.get("signals",[]):
        if not isinstance(row,dict) or row.get("ticker") in observed:
            continue
        try:
            signal_day=date.fromisoformat(row["date"])
            verified=datetime.fromisoformat(row["scanner_verified_at"].replace("Z","+00:00"))
            if verified.tzinfo is None or not 0 <= (now-verified).total_seconds() <= 18*3600:
                continue
            q=row["quantitativeDiagnostics"]
            amount=q["averageDollarVolume20"]
            if (row.get("early_setup_policy_version")!=EARLY_SETUP_POLICY_VERSION or
                row.get("source")!="yahoo:daily_ohlcv" or
                signal_day!=now.date() and (now.date()-signal_day).days not in (1,2,3) or
                not isinstance(amount,(int,float)) or not math.isfinite(amount) or amount<5_000_000 or
                not q.get("liquidityCurrencySource") or not q.get("liquidityFxReferenceDate") or
                row.get("vcpConfirmed") is not True):
                continue
        except (KeyError,TypeError,ValueError,AttributeError):
            continue
        retained.append(row)
    return retained

def scanner_coverage_audit(previous:dict, scanned:list[str], successful:list[str], now:datetime, eligible:int, retained:list[dict], fresh:list[dict], *, eligible_tickers:set[str]|None=None)->dict:
    """24h observed OHLCV coverage; attempted names never count as successful."""
    horizon=24*3600
    old={}
    if previous.get("schema")=="vestra_prebreakout_v1":
        for item in previous.get("coverage_observations_24h",[]):
            if not isinstance(item,dict) or not isinstance(item.get("ticker"),str):
                continue
            try:
                verified=datetime.fromisoformat(item["verified_at"].replace("Z","+00:00"))
                if verified.tzinfo is not None and 0 <= (now-verified).total_seconds() <= horizon:
                    old[item["ticker"]]=verified
            except (KeyError,AttributeError,TypeError,ValueError):
                continue
    prior_verified=set(old)
    successful_distinct=set(successful)
    fresh_verified=successful_distinct-prior_verified
    repeat_verified=successful_distinct&prior_verified
    for ticker in successful_distinct:
        old[ticker]=now
    seen=set(scanned)
    previous_rows=previous.get("signals",[]) if isinstance(previous.get("signals"),list) else []
    prior={r["ticker"]:r for r in previous_rows if isinstance(r,dict) and isinstance(r.get("ticker"),str)}
    present={r["ticker"] for r in retained+fresh if isinstance(r,dict) and isinstance(r.get("ticker"),str)}
    invalidated=sum(t in seen and t not in present for t in prior)
    expired=sum(t not in seen and t not in present for t in prior)
    # Count only observed tickers in the current eligible universe for a
    # percentage. Keep the rolling observations unfiltered for audit/history.
    current_verified = len(set(old) & eligible_tickers) if eligible_tickers is not None else len(old)
    outside_current = len(old) - current_verified
    if eligible_tickers is not None and len(eligible_tickers) != eligible:
        raise ValueError("eligible universe and ticker identities disagree")
    return {"window_hours":24,"distinct_ohlcv_tickers":len(old),
            "current_eligible_verified_distinct":current_verified,
            "outside_current_universe_distinct":outside_current,
            "slot_verified_distinct":len(successful_distinct),
            "slot_new_verified_24h":len(fresh_verified),
            "slot_repeat_verified_24h":len(repeat_verified),
            "slot_repeat_verified_pct":round(100*len(repeat_verified)/len(successful_distinct),2) if successful_distinct else None,
            "eligible_universe":eligible,
            "coverage_pct":round(100*current_verified/eligible,2) if eligible else None,
            "rechecked_removed":invalidated,"not_rechecked_removed":expired,
            "definitions":"OHLCV coverage is observed, not eligible signal coverage; removed counts are previous published rows absent in this scan",
            "observations":[{"ticker":t,"verified_at":v.isoformat()} for t,v in sorted(old.items())]}

def earnings_event_diagnostic(path:Path, as_of:date, tickers:list[str])->dict:
    """Unknown future coverage is not a clean earnings risk gate."""
    result={"status":"unavailable","future_events_in_feed":0,"candidates_with_upcoming_10d":0,
            "candidates_with_no_known_event":None,"interpretation":"unknown_not_clear"}
    try:
        feed=json.loads(path.read_text(encoding="utf-8"))
        if feed.get("schema")!="vestra_earnings_events_v1" or not isinstance(feed.get("events"),list):
            return result
    except (OSError,ValueError,TypeError):
        return result
    future={};future_total=0
    for item in feed["events"]:
        if not isinstance(item,dict) or item.get("kind")!="earnings" or not isinstance(item.get("ticker"),str):
            continue
        try: day=date.fromisoformat(item["date"])
        except (KeyError,ValueError,TypeError): continue
        if day<=as_of: continue
        future_total+=1
        if (day-as_of).days<=10:
            ticker=item["ticker"];future[ticker]=min(day,future.get(ticker,day))
    if not future_total:
        return {**result,"status":"no_future_event_coverage"}
    known={t:future[t].isoformat() for t in tickers if t in future}
    return {**result,"status":"partial_calendar_evidence","future_events_in_feed":future_total,
            "candidates_with_upcoming_10d":len(known),"upcoming_dates":known,
            "interpretation":"not_listed_does_not_mean_clear"}

def safe_quote_currency(provider, ticker):
    """Provider timeouts/rate limits cannot abort the entire scan slot."""
    try:
        return provider.Ticker(ticker).fast_info.get("currency")
    except Exception:
        return None


def batch_has_no_usable_close(data, group):
    """Detect a provider-wide empty/NaN response, not missing individual tickers.

    A successful HTTP/download return does not mean Yahoo supplied valid
    OHLCV. Check every requested ticker before accepting the batch; never
    impute or discard partially missing ticker histories here.
    """
    if data is None or getattr(data, "empty", True):
        return True
    for ticker in group:
        try:
            frame = single_ticker_ohlcv_frame(data, ticker)
            closes = frame["Close"]
            for value in closes:
                try:
                    if not isinstance(value, bool) and math.isfinite(float(value)) and float(value) > 0:
                        return False
                except (TypeError, ValueError, OverflowError):
                    continue
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
    return True


def fetch_ohlcv_batch(provider, group):
    """Retry provider-wide empty/NaN data as well as raised exceptions.

    After two failures mark the *batch unobserved*, never a technical rejection.
    Individual malformed histories remain subject to strict scan_bars checks.
    """
    failures=[]
    for attempt in range(2):
        try:
            data=provider.download(group,period="18mo",interval="1d",group_by="ticker",
                                   auto_adjust=True,threads=False,progress=False,timeout=25)
            if batch_has_no_usable_close(data, group):
                failures.append("provider_batch_without_usable_close")
                continue
            return data,len(failures)
        except Exception as exc:
            failures.append(type(exc).__name__)
    raise RuntimeError('ohlcv_batch_failed_after_retry:'+','.join(failures))

def provider_calendar_batches(tickers, batch_size=15):
    """Avoid mixing Yahoo quoted-suffix calendars within a batch outer join.

    A suffix is only a calendar proxy, not verified exchange evidence.
    The strict per-ticker OHLCV checks remain unchanged.
    """
    if type(batch_size) is not int or batch_size < 1:
        raise ValueError("invalid OHLCV batch size")
    cohorts={}
    for ticker in tickers:
        suffix=ticker.rpartition(".")[2] if "." in ticker else ""
        cohorts.setdefault(suffix,[]).append(ticker)
    return [members[start:start+batch_size]
            for members in cohorts.values()
            for start in range(0,len(members),batch_size)]


def slot_quality_audit(telemetry:dict, coverage:dict)->dict:
    """Assess observed scan quality, never claim complete coverage from capacity."""
    attempted=telemetry["rows_attempted"]
    evaluable=telemetry["rows_evaluable"]
    missing=telemetry["rows_without_ohlcv"]
    processing=telemetry["rows_with_processing_error"]
    failed=telemetry["batches_failed"]
    count=telemetry["batches_attempted"]
    unique=coverage.get("distinct_ohlcv_tickers",0)
    universe=coverage.get("eligible_universe",0)
    if not all(type(x) is int and x>=0 for x in
               (attempted,evaluable,missing,processing,failed,count,unique,universe)):
        raise ValueError("invalid scanner telemetry")
    if evaluable>attempted or missing>attempted or failed>count:
        raise ValueError("inconsistent scanner telemetry")
    current=coverage.get("current_eligible_verified_distinct",unique)
    if type(current) is not int or current<0 or (universe and current>universe):
        raise ValueError("invalid current universe coverage")
    full=bool(universe and current==universe)
    return {"status":"full_observed_24h" if full else "partial_observed_24h",
            "observed_24h_coverage_pct":coverage.get("coverage_pct"),
            "full_universe_verified":full,
            "slot_evaluable_pct":round(100*evaluable/attempted,2) if attempted else None,
            "slot_missing_ohlcv":missing,"slot_processing_errors":processing,
            "slot_failed_batches":failed,
            "interpretation":"observed_data_only_not_a_quality_or_edge_forecast"}


def main():
    import yfinance as yf
    now=datetime.now(timezone.utc)
    index_bytes=INDEX.read_bytes()
    stocks=json.loads(index_bytes).get("stocks",[])
    watch=watched_tickers(now)
    try:
        previous=json.loads(OUTPUT.read_text(encoding="utf-8"))
    except (OSError,ValueError):
        previous={}
    prior_verified=set()
    if previous.get("schema")=="vestra_prebreakout_v1":
        for record in previous.get("coverage_observations_24h",[]):
            if not isinstance(record,dict) or not isinstance(record.get("ticker"),str):
                continue
            try:
                verified=datetime.fromisoformat(str(record["verified_at"]).replace("Z","+00:00"))
                if verified.tzinfo is not None and 0 <= (now-verified).total_seconds() <= 24*3600:
                    prior_verified.add(record["ticker"])
            except (KeyError,TypeError,ValueError,AttributeError):
                continue
    tickers=candidates(stocks,now.date(),now.hour//6,watch,
                       recently_verified=prior_verified)
    slot_selection_audit={"status":"planned_not_observed",
        "previous_verified_24h":len(prior_verified),
        "selected_not_verified_24h":sum(t not in prior_verified for t in tickers),
        "selected_repeat_verified_24h":sum(t in prior_verified for t in tickers),
        "not_successful_ohlcv_count":True}
    rotation_plan=rotation_plan_audit(stocks,now.date(),watch)
    universe_provenance=universe_provenance_audit(stocks,previous,index_bytes)
    # Coverage refers to this slot, not the entire eligible investment universe.
    eligible=eligible_universe_size(stocks)
    found=[];shadow_cases=[];research_rows=[];checked=0;successful=[];failures=[]
    gate_exclusions={};ma_gate_failure_counts={};invalid_ohlcv_details={}
    geometry_shadow_counts={"examined":0,"base_width_pass":0,"contractions_pass":0,
                            "both_pass":0,"ma_rejected_both_pass":0}
    phase_shadow_counts={"examined":0,"canonical_both_pass":0,
                         "any_phase_both_pass":0,"alternate_phase_only_both_pass":0,
                         "multi_phase_both_pass":0}
    swing_shadow_counts={"examined":0,"three_pullbacks":0,"contracting":0,
                         "narrow_base":0,"near_unbroken_pivot":0,"all_geometry_pass":0}
    missing_close_locations={};missing_close_patterns={}
    padding_rows_trimmed=0;tickers_with_padding_trimmed=0
    trailing_rows_trimmed=0;tickers_with_trailing_trimmed=0
    interior_null_gap_totals={key:0 for key in interior_all_null_gap_diagnostic([])}
    tickers_with_interior_null_gaps=0
    remaining_interior_gap_totals={key:0 for key in interior_all_null_gap_diagnostic([])}
    tickers_with_remaining_interior_gaps=0
    scan_started=time.monotonic();batch_attempted=0;batch_failed=0;batch_completed=0;batch_retries=0;row_failed=0;row_missing_ohlcv=0
    try:
        fx=json.loads((ROOT/"data/fx.json").read_text(encoding="utf-8"))
    except (OSError,ValueError):
        fx={}  # A missing exchange-rate file may never authorize liquidity.
    currency_checked=0;currency_rejected=0
    # Shadow evaluation only; never route legacy candidates to public signals.
    # Re-query only a bounded number of suspect ticker histories per slot.
    recovery_budget=12
    recovery_attempted=0
    recovery_verified=0
    recovery_rejected=0
    recovery_rejection_reasons={}
    shadow={"legacy_eligible":0,"strict_eligible":0,"legacy_only":0,"strict_only":0,"neither":0,"compared":0}
    batches=provider_calendar_batches(tickers)
    for group in batches:
        batch_attempted+=1
        try:
            data,retries=fetch_ohlcv_batch(yf,group)
            batch_retries+=retries
        except RuntimeError as exc:
            batch_failed+=1
            batch_retries+=1
            failures.append(str(exc));continue
        batch_completed+=1
        for ticker in group:
            try:
                frame=single_ticker_ohlcv_frame(data,ticker)
                bars=completed_sessions(dataframe_bars(frame),now.date())
                # Only batch-alignment padding before the first observed bar
                # can be removed. Gaps inside actual trading history remain fatal.
                bars,trimmed=trim_leading_provider_padding(bars)
                bars,trailing_trimmed=trim_trailing_provider_padding(bars)
                gap_profile=interior_all_null_gap_diagnostic(bars)
                terminal_unpriced=bool(bars and all(bars[-1].get(k) is None
                    for k in ("close","high","low")))
                if (gap_profile["gap_runs"] or terminal_unpriced) and recovery_attempted<recovery_budget:
                    recovery_attempted+=1
                    recovery_trace={}
                    try:
                        independent,_=fetch_ohlcv_batch(yf,[ticker])
                        independent_frame=single_ticker_ohlcv_frame(independent,ticker)
                        replacement=completed_sessions(dataframe_bars(independent_frame),now.date())
                        replacement,_=trim_leading_provider_padding(replacement)
                        replacement,_=trim_trailing_provider_padding(replacement)
                        verified=verified_standalone_recovery(bars,replacement,now.date(),audit=recovery_trace)
                    except (RuntimeError,ValueError,TypeError,KeyError) as exc:
                        verified=None
                        recovery_trace["rejection_reason"]="standalone_exception_"+type(exc).__name__
                        failures.append("standalone_recheck:"+ticker+":"+type(exc).__name__)
                    if verified is not None:
                        bars=verified
                        recovery_verified+=1
                    else:
                        recovery_rejected+=1
                        reason=recovery_trace.get("rejection_reason","unclassified_rejection")
                        recovery_rejection_reasons[reason]=recovery_rejection_reasons.get(reason,0)+1
                remaining_gap_profile=interior_all_null_gap_diagnostic(bars)
                tickers_with_remaining_interior_gaps+=int(remaining_gap_profile["gap_runs"]>0)
                for key,value in remaining_gap_profile.items():
                    if key=="max_run_rows":
                        remaining_interior_gap_totals[key]=max(remaining_interior_gap_totals[key],value)
                    else:
                        remaining_interior_gap_totals[key]+=value
                tickers_with_interior_null_gaps+=int(gap_profile["gap_runs"]>0)
                for key,value in gap_profile.items():
                    if key=="max_run_rows":
                        interior_null_gap_totals[key]=max(interior_null_gap_totals[key],value)
                    else:
                        interior_null_gap_totals[key]+=value
                padding_rows_trimmed+=trimmed
                tickers_with_padding_trimmed+=int(trimmed>0)
                trailing_rows_trimmed+=trailing_trimmed
                tickers_with_trailing_trimmed+=int(trailing_trimmed>0)
                checked+=bool(bars)
                row_missing_ohlcv+=int(not bool(bars))
                evaluable=evaluable_recheck(bars,now.date())
                if evaluable:successful.append(ticker)
                trace={}
                signal=scan_bars(ticker,bars,now.date(),liquidity_floor=0,audit=trace)
                first=trace.get('first_rejection','unresolved')
                # Archive negative controls as well as positive signals. A
                # rejected pattern with valid prices is still a real observed
                # opportunity to test subsequent false negatives. No score or
                # success outcome is assigned at capture time.
                last=bars[-1] if evaluable else None
                research_rows.append({"ticker":ticker,"evaluable":evaluable,
                    "last_session":last["date"] if last else None,
                    "adjusted_close":round(float(last["close"]),6) if last else None,
                    "price_basis":"yahoo_auto_adjusted_daily_close" if last else None,
                    "asof_base_price_anchor":trace.get("asof_base_price_anchor"),
                    "first_rejection":first,
                    "trend_phase":trace.get("trend_phase"),
                    "geometry_shadow":trace.get("geometry_shadow"),
                    "ma_structure_shadow":trace.get("ma_structure_shadow"),
                    "research_prebreakout_lineage":trace.get("research_prebreakout_lineage"),
                    "swing_geometry_shadow":trace.get("swing_geometry_shadow"),
                    "geometry_phase_shadow":trace.get("geometry_phase_shadow"),
                    "technical_evidence_shadow":trace.get("technical_evidence_shadow"),
                    "ma_failed_checks":trace.get("moving_average_failed_checks",[]),
                    "no_future_outcome_at_capture":True})
                gate_exclusions[first]=gate_exclusions.get(first,0)+1
                geometry=trace.get("geometry_shadow")
                swing=trace.get("swing_geometry_shadow")
                if isinstance(swing,dict) and swing.get("status")=="measured":
                    swing_shadow_counts["examined"]+=1
                    swing_shadow_counts["three_pullbacks"]+=int(swing.get("legs_found",0)>=3)
                    swing_shadow_counts["contracting"]+=int(swing.get("sequential_contraction_pass") is True)
                    swing_shadow_counts["narrow_base"]+=int(swing.get("base_width_pass") is True)
                    swing_shadow_counts["near_unbroken_pivot"]+=int(swing.get("below_pivot_pass") is True)
                    swing_shadow_counts["all_geometry_pass"]+=int(swing.get("all_geometry_pass") is True)
                phase=trace.get("geometry_phase_shadow")
                if isinstance(phase,dict):
                    phase_shadow_counts["examined"]+=1
                    canonical=phase.get("canonical_both_pass") is True
                    both=phase.get("both_pass_count",0)
                    phase_shadow_counts["canonical_both_pass"]+=int(canonical)
                    phase_shadow_counts["any_phase_both_pass"]+=int(both>0)
                    phase_shadow_counts["alternate_phase_only_both_pass"]+=int(both>0 and not canonical)
                    phase_shadow_counts["multi_phase_both_pass"]+=int(both>=3)
                if isinstance(geometry,dict):
                    geometry_shadow_counts["examined"]+=1
                    for key in ("base_width_pass","contractions_pass","both_pass"):
                        geometry_shadow_counts[key]+=int(geometry.get(key) is True)
                    if first=="moving_average_structure" and geometry.get("both_pass") is True:
                        geometry_shadow_counts["ma_rejected_both_pass"]+=1
                if first=="invalid_ohlcv_or_date":
                    detail=trace.get("invalid_ohlcv_detail","unclassified")
                    invalid_ohlcv_details[detail]=invalid_ohlcv_details.get(detail,0)+1
                    if detail=="invalid_or_missing_close":
                        position=trace.get("missing_close_bar_location","unclassified")
                        pattern=trace.get("missing_close_pattern","unclassified")
                        missing_close_locations[position]=missing_close_locations.get(position,0)+1
                        missing_close_patterns[pattern]=missing_close_patterns.get(pattern,0)+1
                if first=="moving_average_structure":
                    for failed_check in trace.get("moving_average_failed_checks",[]):
                        ma_gate_failure_counts[failed_check]=ma_gate_failure_counts.get(failed_check,0)+1
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
                    currency=safe_quote_currency(yf,ticker)
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
                    signal["scanner_verified_at"]=now.isoformat()
                    found.append(signal)
            except (KeyError,ValueError,TypeError) as exc:
                row_failed+=1
                failures.append(f"{ticker}:{type(exc).__name__}")
    # A failed OHLCV download is not an observed rejection. Invalidate only a\n    # ticker whose bars were actually read; per-row 18h expiry still applies.
    # A rechecked ticker which now fails must disappear; never promote stale cache.
    retained=recent_verified_signals(previous,successful,now)
    by={signal["ticker"]:signal for signal in retained}
    by.update({signal["ticker"]:signal for signal in found})
    audit=scanner_coverage_audit(previous,successful,successful,now,eligible,retained,found,
                                 eligible_tickers=eligible_universe_tickers(stocks))
    earnings_risks=earnings_risk_from_latest(ROOT/'data/earnings-latest.json',now.date(),list(by))
    for signal in by.values(): signal['earningsRiskGate']=earnings_risks.get(signal['ticker'],{'status':'unknown'})
    published,focus=published_signals_with_focus(list(by.values()),now.date(),earnings_risks=earnings_risks)
    earnings_audit=earnings_event_diagnostic(ROOT/"data/earnings-events.json",now.date(),[r["ticker"] for r in published])
    slot_telemetry={"batches_attempted":batch_attempted,"batches_completed":batch_completed,
        "batches_failed":batch_failed,"batches_retried":batch_retries,"rows_attempted":len(tickers),
        "rows_with_any_ohlcv":checked,"rows_without_ohlcv":row_missing_ohlcv,
        "rows_with_processing_error":row_failed,"rows_evaluable":len(set(successful)),
        "duration_seconds":round(time.monotonic()-scan_started,3),
        "measurement":"slot_observed_not_full_universe_or_provider_rate_limit_estimate"}
    observed_names={row["ticker"] for row in research_rows}
    research_rows.extend({"ticker":ticker,"evaluable":False,"last_session":None,
        "adjusted_close":None,"price_basis":None,
        "first_rejection":"provider_batch_unobserved","geometry_shadow":None,
        "ma_failed_checks":[],"no_future_outcome_at_capture":True}
        for ticker in tickers if ticker not in observed_names)
    scan_quality=slot_quality_audit(slot_telemetry,audit)
    # Data-provider failures must be visible independently of pattern scarcity.
    # No missing prices are patched or interpreted as negative setups.
    invalid_rows=gate_exclusions.get("invalid_ohlcv_or_date",0)
    invalid_pct=round(100*invalid_rows/len(tickers),2) if tickers else None
    scan_quality["invalid_ohlcv_slot_pct"]=invalid_pct
    scan_quality["ohlcv_integrity_alert"]=bool(invalid_pct is not None and invalid_pct>10)
    scan_quality["ohlcv_integrity_alert_reason"]=(
        "more_than_10_pct_invalid_ohlcv_in_current_slot"
        if scan_quality["ohlcv_integrity_alert"] else None)
    observed_features=[r["technical_evidence_shadow"] for r in research_rows
        if r.get("evaluable") is True and isinstance(r.get("technical_evidence_shadow"),dict)
        and r["technical_evidence_shadow"].get("status")=="measured"]
    feature_fields=("atr14_pct","atr14_to_atr60","realized_vol10_to_vol40",
                    "volume9_to_prior40","return20_pct","return60_pct",
                    "efficiency20","close_position20")
    feature_audit={"scope":"current_slot_evaluable_ohlcv_including_rejected_patterns",
        "measured_rows":len(observed_features),
        "available_by_metric":{key:sum(type(f.get(key)) in (int,float)
            and math.isfinite(f[key]) for f in observed_features) for key in feature_fields},
        "atr_contraction_below_0_8":sum(type(f.get("atr14_to_atr60")) in (int,float)
            and f["atr14_to_atr60"]<.8 for f in observed_features),
        "volume_dry_below_0_8":sum(type(f.get("volume9_to_prior40")) in (int,float)
            and f["volume9_to_prior40"]<.8 for f in observed_features),
        "index_relative_strength_unobserved":True,
        "not_an_eligibility_gate_or_predictive_validation":True}
    # A scanner version is part of evidence provenance. Older signals must not
    # be carried into a new model merely because their timestamps are fresh.
    for signal in published:
        signal["early_setup_policy_version"] = EARLY_SETUP_POLICY_VERSION
    payload={"schema":"vestra_prebreakout_v1","generated_at":now.isoformat(),
             "early_setup_policy_version":EARLY_SETUP_POLICY_VERSION,
             "attempted":len(tickers),"with_ohlcv":checked,"evaluable_ohlcv":len(set(successful)),"eligible_universe":eligible,"universe_provenance_audit":universe_provenance,"coverage_this_slot":round(checked/eligible,4) if eligible else None,"coverage_scope":"rotating_single_scan_slot_not_full_universe","daily_capacity_ceiling":daily_coverage_capacity(eligible),"rotation_plan_audit":rotation_plan,"slot_selection_audit":slot_selection_audit,"scan_unique_tickers":len(set(tickers)),"download_batches_planned":len(batches),"download_batch_size":15,"provider_batch_grouping":"quoted_suffix_calendar_proxy_not_verified_exchange","scan_slot_telemetry":slot_telemetry,"scan_quality_audit":scan_quality,"scan_anchor_duplicates":0,"new_signals":len(found),"retained_verified_signals":len(retained),"ranked_scope":"verified_recent_cross_slot_not_full_universe","coverage_audit_24h":{k:v for k,v in audit.items() if k!="observations"},"coverage_observations_24h":audit["observations"],"liquidity_currency_checked":currency_checked,"liquidity_currency_rejected":currency_rejected,"quality_model":"vcp_before_pivot_v3","scan_slot_utc":now.hour//6,
             "research_observations":{"scope":"current_observed_slot_only","source":"yahoo_auto_adjusted_daily_ohlcv",
                 "captured_at":now.isoformat(),"rows":sorted(research_rows,key=lambda r:r["ticker"]),
                 "point_in_time_capture_not_historical_reconstruction":True,
                 "no_future_labels_or_success_probabilities":True},
             "errors":failures[:8],"gate_funnel":{"scope":"current_observed_slot_only","method":"first_failing_gate_in_order_not_independent_gate_intersections",
                 "observed_rows":sum(gate_exclusions.values()),"first_rejection_counts":dict(sorted(gate_exclusions.items())),
                 "structurally_passed":gate_exclusions.get("passed_structural_gates",0),
                 "currency_or_usd_liquidity_rejections_after_structural_pass":currency_rejected,
                 "missing_downloads_not_negative_evidence":True,"probability_or_forward_performance":None},
             "provider_padding_audit":{"scope":"boundary_all_four_ohlcv_null_only",
                 "tickers_with_trimmed_prefix":tickers_with_padding_trimmed,
                 "null_prefix_rows_trimmed":padding_rows_trimmed,
                 "tickers_with_trimmed_suffix":tickers_with_trailing_trimmed,
                 "null_suffix_rows_trimmed":trailing_rows_trimmed,
                 "interior_or_partial_rows_never_trimmed":True,
                 "not_eligibility_or_performance":True},
             "vcp_phase_robustness_audit":{**phase_shadow_counts,
                 "method":"fixed_20_session_windows_shifted_0_to_10_past_sessions",
                 "research_only_not_signal_or_backtest":True},
             "vcp_swing_geometry_audit":{**swing_shadow_counts,
                 "method":"confirmed_radius3_local_extrema_last120_closed_bars",
                 "research_only_no_promotion_or_backtest":True},
             "technical_feature_audit":feature_audit,
             "standalone_gap_recovery_audit":{"method":"independent_single_ticker_ohlcv_with_exact_overlap_checks",
                 "attempted":recovery_attempted,"verified":recovery_verified,
                 "rejected":recovery_rejected,"max_per_slot":recovery_budget,
                 "rejection_reason_counts":dict(sorted(recovery_rejection_reasons.items())),
                 "no_imputation":True,"not_signal_or_performance":True},
             "interior_all_null_gap_audit":{"scope":"all_observed_slot_series_diagnostic_only",
                 "measurement_stage":"before_independent_recovery",
                 "tickers_with_gaps":tickers_with_interior_null_gaps,
                 **interior_null_gap_totals,
                 "weekday_is_not_proof_of_trading_session":True,
                 "no_rows_removed_or_imputed":True,
                 "not_strategy_performance":True},
             "remaining_interior_all_null_gap_audit":{"scope":"all_observed_slot_series_after_independent_recovery",
                 "tickers_with_gaps":tickers_with_remaining_interior_gaps,
                 **remaining_interior_gap_totals,
                 "no_rows_removed_or_imputed":True,
                 "not_strategy_performance":True},
             "invalid_ohlcv_detail_audit":{"scope":"first_invalid_bar_in_current_slot",
                 "first_rejected_rows":gate_exclusions.get("invalid_ohlcv_or_date",0),
                 "reason_counts":dict(sorted(invalid_ohlcv_details.items())),
                 "missing_close_bar_location_counts":dict(sorted(missing_close_locations.items())),
                 "missing_close_row_pattern_counts":dict(sorted(missing_close_patterns.items())),
                 "diagnostic_only_no_bar_repair":True,
                 "not_strategy_performance":True},
              "moving_average_failure_audit":{"scope":"first_rejected_by_moving_average_in_current_slot",
                  "method":"nonexclusive_failed_conditions_not_independent_gate_pass_rates",
                  "first_rejected_rows":gate_exclusions.get("moving_average_structure",0),
                  "failed_condition_counts":dict(sorted(ma_gate_failure_counts.items())),
                  "not_signal_or_forward_performance":True},
             "independent_base_geometry_audit":{"scope":"current_slot_valid_fresh_histories_including_ma_rejections",
                 "method":"same_observed_bars_no_ma_eligibility_override",
                 **geometry_shadow_counts,"not_signal_or_forward_performance":True},
             "quality_filter_shadow":{"method":"same_bars_current_slot_counterfactual_not_historical_backtest","not_probability":True,**shadow},
             "quality_shadow_cases":{"purpose":"prospective_same_slot_comparison_not_dashboard_candidates",
                  "outcomes_available":False,"records":sorted(shadow_cases,key=lambda x:(x["ticker"],x["date"]))},
             "daily_focus":focus,"earnings_event_diagnostic":earnings_audit,
             "earnings_pick_gate":{"method":"conservative_17_calendar_day_proxy_not_exact_exchange_sessions",
                 "unknown":sum(v["status"]=="unknown" for v in earnings_risks.values()),
                 "near_term":sum(v["status"]=="near_term" for v in earnings_risks.values()),
                 "dated_beyond_buffer":sum(v["status"]=="dated_beyond_buffer" for v in earnings_risks.values())},
             "signals":published}
    OUTPUT.write_text(json.dumps(payload,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in payload.items() if k!="signals"}))

if __name__=="__main__":main()
