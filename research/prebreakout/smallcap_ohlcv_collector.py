#!/usr/bin/env python3
"""Independent, bounded *observed* OHLCV collector for USD 100m–2b small caps.

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
from scripts.refresh_prebreakout_scanner import EARLY_SETUP_POLICY_VERSION
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
            or not 100_000_000<=cap<=2_000_000_000):continue
        found[symbol]=float(cap)
    return sorted(set(found)-ambiguous)

def technical_structure_audit(observations):
    """Nonexclusive failed MA checks on evaluable, MA-rejected series only."""
    ma_rows=[row for row in observations
             if row.get("status")=="evaluable_ohlcv" and
             row.get("technical_first_rejection")=="moving_average_structure"]
    examined=[row for row in ma_rows if isinstance(row.get("technical_failed_ma_checks"),list)]
    return {"ma_rejected_rows":len(ma_rows),"diagnosed_ma_rejected_rows":len(examined),
            "nonexclusive_failed_check_counts":dict(sorted(Counter(
                check for row in examined for check in row["technical_failed_ma_checks"]).items())),
            "not_independent_pass_rates":True}

def independent_geometry_audit(observations):
    """Independent geometry on all *current* evaluable, liquidity-qualified rows.

    MA rejection does not prevent counting base/VCP geometry. The counts are
    diagnostic only and cannot qualify a setup or bypass a later risk gate.
    """
    eligible=[row for row in observations if row.get("status")=="evaluable_ohlcv"
              and row.get("technical_first_rejection")!="below_1m_usd_turnover"]
    observed=[row for row in eligible if isinstance(row.get("technical_geometry_shadow"),dict)]
    counts={key:sum(row["technical_geometry_shadow"].get(key) is True for row in observed)
            for key in ("base_width_pass","contractions_pass","both_pass")}
    measures=("prior_width_pct","base_width_pct","w1_pct","w2_pct","w3_pct")
    quantified=sum(all(type(row["technical_geometry_shadow"].get(key)) in (int,float)
                       and math.isfinite(row["technical_geometry_shadow"][key])
                       for key in measures) for row in observed)
    return {"scope":"evaluable_liquid_series_including_ma_rejections",
            "liquid_evaluable_rows":len(eligible),"geometry_diagnosed_rows":len(observed),
            "continuous_geometry_measurement_rows":quantified,
            "legacy_boolean_only_geometry_rows":len(observed)-quantified,
            **counts,"not_eligibility_or_success_probability":True}


def phase_robustness_audit(observations):
    """Measure fixed-window phase sensitivity without qualifying a setup."""
    measured=[]
    for row in observations:
        if row.get("status")!="evaluable_ohlcv" or row.get("technical_first_rejection")=="below_1m_usd_turnover":
            continue
        phase=row.get("technical_geometry_phase_shadow")
        if not isinstance(phase,dict):continue
        counts=[phase.get(k) for k in ("base_width_pass_count","contractions_pass_count","both_pass_count")]
        if not all(type(v) is int and 0<=v<=11 for v in counts):continue
        if type(phase.get("canonical_both_pass")) is not bool:continue
        measured.append(phase)
    return {"scope":"evaluable_liquid_series_with_11_historical_phases",
            "measured_rows":len(measured),
            "canonical_both_pass":sum(p["canonical_both_pass"] for p in measured),
            "any_phase_both_pass":sum(p["both_pass_count"]>0 for p in measured),
            "alternate_phase_only_both_pass":sum(p["both_pass_count"]>0 and not p["canonical_both_pass"] for p in measured),
            "multi_phase_both_pass":sum(p["both_pass_count"]>=3 for p in measured),
            "not_eligibility_or_backtest":True}


def swing_geometry_audit(observations):
    """Compare variable-length price-swing geometry with fixed 20-session bins.

    Only observed, liquid, evaluable historical bars count. The alternative
    geometry never promotes securities into the verified signals list.
    """
    measured=[]
    for row in observations:
        if row.get("status")!="evaluable_ohlcv" or row.get("technical_first_rejection")=="below_1m_usd_turnover":
            continue
        swing=row.get("technical_swing_geometry_shadow")
        if isinstance(swing,dict) and swing.get("status")=="measured":
            measured.append(swing)
    return {"scope":"liquid_evaluable_series_with_confirmed_local_extrema",
            "measured_rows":len(measured),
            "three_pullbacks":sum(x.get("legs_found",0)>=3 for x in measured),
            "sequential_contraction_pass":sum(x.get("sequential_contraction_pass") is True for x in measured),
            "base_width_pass":sum(x.get("base_width_pass") is True for x in measured),
            "all_geometry_pass":sum(x.get("all_geometry_pass") is True for x in measured),
            "research_only_no_signal_promotion_or_performance_claim":True}


def technical_evidence_audit(observations):
    """Feature completeness, not a fitted predictor or feature-weight score."""
    eligible=[row for row in observations if row.get("status")=="evaluable_ohlcv"
              and row.get("technical_first_rejection")!="below_1m_usd_turnover"]
    measured=[row["technical_evidence_shadow"] for row in eligible
              if isinstance(row.get("technical_evidence_shadow"),dict)
              and row["technical_evidence_shadow"].get("status")=="measured"]
    metrics=("atr14_pct","atr14_to_atr60","realized_vol10_to_vol40",
             "volume9_to_prior40","return20_pct","return60_pct",
             "efficiency20","close_position20")
    available={key:sum(type(r.get(key)) in (int,float) and math.isfinite(r[key])
                       for r in measured) for key in metrics}
    return {"scope":"liquid_evaluable_series_independent_of_first_rejection",
            "eligible_rows":len(eligible),"measured_rows":len(measured),
            "available_by_metric":available,
            "atr_contraction_below_0_8":sum(type(r.get("atr14_to_atr60")) in (int,float)
                and r["atr14_to_atr60"]<.8 for r in measured),
            "volume_dry_below_0_8":sum(type(r.get("volume9_to_prior40")) in (int,float)
                and r["volume9_to_prior40"]<.8 for r in measured),
            "relative_strength_observed_rows":0,
            "not_independent_predictive_validation_or_signal":True}


def swing_watch_observations(observations, limit=8):
    """Inspectable price structures, explicitly below signal eligibility."""
    watch=[]
    for row in observations:
        if row.get("status")!="evaluable_ohlcv" or row.get("verified_prebreakout_setup"):
            continue
        g=row.get("technical_swing_geometry_shadow")
        volume=row.get("average_dollar_volume_20_usd")
        if (not isinstance(g,dict) or g.get("all_geometry_pass") is not True or
            type(volume) not in (int,float) or not math.isfinite(volume) or volume<1_000_000 or
            not isinstance(row.get("last_session"),str)):
            continue
        watch.append({"ticker":row["ticker"],"last_session":row["last_session"],
            "leg_depths_pct":g["leg_depths_pct"],
            "base_width_pct":g["base_width_pct"],
            "distance_to_resistance_pct":g["distance_to_resistance_pct"],
            "first_rejection":row.get("technical_first_rejection"),
            "technical_evidence":row.get("technical_evidence_shadow"),
            "status":"swing_geometry_research_not_signal",
            "missing_volume_ma_lineage_and_independent_forward_validation":True})
    return sorted(watch,key=lambda x:(x["distance_to_resistance_pct"],x["ticker"]))[:limit]


def geometry_watch_observations(observations, as_of, limit=12):
    """Observable partial geometry, never a VCP signal or score.

    Only fully quantified, recent, USD-liquid series enter this diagnostic
    watch tier. Passing one geometry test does not override the failed one,
    the moving-average structure or the unverified spread/earnings gates.
    """
    from datetime import date as date_type
    today=as_of.date() if isinstance(as_of,datetime) else as_of
    if not isinstance(today,date_type):raise ValueError("invalid observation date")
    out=[]
    measures=("prior_width_pct","base_width_pct","w1_pct","w2_pct","w3_pct")
    for row in observations:
        if row.get("status")!="evaluable_ohlcv" or row.get("verified_prebreakout_setup"):
            continue
        turnover=row.get("average_dollar_volume_20_usd")
        if type(turnover) not in (int,float) or not math.isfinite(turnover) or turnover<1_000_000:
            continue
        geometry=row.get("technical_geometry_shadow")
        if not isinstance(geometry,dict) or not all(type(geometry.get(k)) in (int,float)
                                                       and math.isfinite(geometry[k]) for k in measures):
            continue
        base=geometry.get("base_width_pass") is True
        contractions=geometry.get("contractions_pass") is True
        if base==contractions:continue
        try:session=date_type.fromisoformat(str(row["last_session"])[:10])
        except (KeyError,TypeError,ValueError):continue
        if not 0<=(today-session).days<=7:continue
        out.append({"ticker":row["ticker"],"last_session":session.isoformat(),
                    "average_dollar_volume_20_usd":turnover,
                    "base_width_pass":base,"contractions_pass":contractions,
                    "base_width_pct":geometry["base_width_pct"],
                    "prior_width_pct":geometry["prior_width_pct"],
                    "contraction_widths_pct":[geometry[k] for k in ("w1_pct","w2_pct","w3_pct")],
                    "technical_first_rejection":row.get("technical_first_rejection"),
                    "technical_evidence":row.get("technical_evidence_shadow"),
                    "moving_average_failed_checks":row.get("technical_failed_ma_checks") or [],
                    "status":"partial_geometry_observation_not_signal"})
    return sorted(out,key=lambda r:r["ticker"])[:limit]

def cohort_churn_audit(current,previous,observations):
    """Reconcile exact small-cap universe membership across canonical slots.

    The old report's fingerprint alone cannot establish which names entered or
    exited. Never infer cohort turnover from changes in the denominator.
    """
    now=current.get("universe_tickers")
    before=previous.get("universe_tickers") if isinstance(previous,dict) else None
    if not isinstance(now,list) or not isinstance(before,list):
        return {"status":"previous_exact_membership_unavailable",
                "added":None,"removed":None,"retained":None,
                "not_market_cap_point_in_time_history":True}
    now_set=set(now);before_set=set(before)
    if len(now_set)!=len(now) or len(before_set)!=len(before):
        raise ValueError("smallcap cohort roster contains duplicate tickers")
    added=now_set-before_set
    retained=now_set&before_set
    evaluable={str(row.get("ticker") or "").upper() for row in observations
               if row.get("status")=="evaluable_ohlcv"}
    return {"status":"exact_roster_compared","added":len(added),
            "removed":len(before_set-now_set),"retained":len(retained),
            "newly_added_evaluable":len(added&evaluable),
            "retained_evaluable":len(retained&evaluable),
            "newly_added_unobserved":len(added-{str(row.get("ticker") or "").upper()
                                                for row in observations}),
            "not_market_cap_point_in_time_history":True}

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
        # The technical engine only consumes the latest 252 closed sessions.
        # Invalid older provider bars cannot affect a current 52-week/VCP
        # setup and must not erase the otherwise usable recent observation.
        from collections import deque
        for timestamp,row in deque(frame.iterrows(),maxlen=253):
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
    technical_audit={}
    if turnover>=1_000_000:
        setup=scan_bars(ticker,full_bars,checked_at.date(),
                        strict_quality=True,liquidity_floor=1_000_000,
                        audit=technical_audit)
    technical_first_rejection=(technical_audit.get("first_rejection","unresolved")
                               if turnover>=1_000_000 else "below_1m_usd_turnover")
    if setup:
        setup={**setup,"source":"yahoo:smallcap_daily_ohlcv",
               "currencyVerified":"USD","spreadVerified":False,
               "gapRisk":"not_verified","earningsRiskGate":"unknown",
               "observedAt":checked_at.isoformat()}
    return {"ticker":ticker,"status":"evaluable_ohlcv","bars":len(clean),
            "last_adjusted_close":round(clean[-1][1],6),
            "zero_volume_sessions_before_contiguous_window":zero_volume_sessions,
            "verified_prebreakout_setup":setup,
            "technical_first_rejection":technical_first_rejection,
            "technical_geometry_shadow":technical_audit.get("geometry_shadow")
                if turnover>=1_000_000 else None,
            "technical_geometry_phase_shadow":technical_audit.get("geometry_phase_shadow")
                if turnover>=1_000_000 else None,
            "technical_swing_geometry_shadow":technical_audit.get("swing_geometry_shadow")
                if turnover>=1_000_000 else None,
            "technical_evidence_shadow":technical_audit.get("technical_evidence_shadow")
                if turnover>=1_000_000 else None,
            "technical_failed_ma_checks":technical_audit.get("moving_average_failed_checks",[])
                if technical_first_rejection=="moving_average_structure" else None,
            "first_session":clean[0][0],"last_session":last,
            "average_dollar_volume_20_usd":round(turnover,2),
            "liquidity_5m_usd_verified":turnover>=5_000_000,
            "spread_verified":False,"gap_risk_not_assessed":True,
            "currency":"USD","price_basis":"yfinance_auto_adjusted",
            "ohlcv_observed_at":checked_at.isoformat()}

def pick_research_tickers(names,slot,budget,previous,checked_at,ttl_hours=96,
                          failure_retry_hours=24):
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
    needs_geometry={}
    needs_continuous={}
    needs_price={}
    needs_policy={}
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
            # Once data coverage is addressed, revisit usable but historically
            # unquantified VCP geometry before already quantified OHLCV. Never
            # waste a geometry request on verified sub-$1m daily turnover.
            turnover=row.get("average_dollar_volume_20_usd")
            liquid=(type(turnover) in (int,float) and math.isfinite(turnover)
                    and turnover>=1_000_000)
            needs_policy[ticker]=(last_status[ticker]=="evaluable_ohlcv" and liquid and
                row.get("early_setup_policy_version")!=EARLY_SETUP_POLICY_VERSION)
            price=row.get("last_adjusted_close")
            needs_price[ticker]=(last_status[ticker]=="evaluable_ohlcv" and liquid
                and (type(price) not in (int,float) or not math.isfinite(price)
                     or price<=0))
            needs_continuous[ticker]=(last_status[ticker]=="evaluable_ohlcv"
                and row.get("technical_first_rejection")!="below_1m_usd_turnover"
                and (liquid or turnover is None)
                and (not isinstance(row.get("technical_geometry_shadow"),dict)
                     or not all(type(row["technical_geometry_shadow"].get(k)) in (int,float)
                         and math.isfinite(row["technical_geometry_shadow"][k])
                         for k in ("prior_width_pct","base_width_pct","w1_pct","w2_pct","w3_pct"))))
            phase=row.get("technical_geometry_phase_shadow")
            needs_phase=(not isinstance(phase,dict)
                         or type(phase.get("both_pass_count")) is not int
                         or not 0<=phase["both_pass_count"]<=11)
            needs_geometry[ticker]=(needs_price[ticker] or needs_continuous[ticker] or needs_policy[ticker] or
                (last_status[ticker]=="evaluable_ohlcv" and liquid and needs_phase))
    # Recent failures cannot be cured by immediately requesting the same
    # ticker again every six hours. Allow a bounded retry delay so that the
    # independent VCP geometry backlog makes progress when the unseen cohort
    # is exhausted. After 24h, failures regain priority over geometry.
    retry_cutoff=checked_at-timedelta(hours=failure_retry_hours)
    ordered=sorted(rotated,key=lambda ticker:(
        0 if ticker not in last_seen else
        (1 if last_status.get(ticker)!="evaluable_ohlcv"
              and last_seen[ticker]<=retry_cutoff else
         2 if needs_continuous.get(ticker) else
         3 if needs_price.get(ticker) else
         4 if needs_policy.get(ticker) or needs_geometry.get(ticker) else
         5 if last_status.get(ticker)!="evaluable_ohlcv" else 6),
        last_seen.get(ticker,cutoff)))
    # Reserve one third of the bounded slot for missing adjusted close,
    # continuous geometry or the 11-phase measurement. A legacy, evaluable
    # observation without a dated price cannot enter a prospective outcome
    # cohort; it must be refreshed without displacing the unseen-universe lane.
    # Previously, 70+ unseen tickers could
    # occupy consecutive slots while 100+ valid histories stayed unquantified.
    # Keep the other two thirds available for unseen names and failed retries.
    # A due-failure backlog can also monopolize a slot after every ticker
    # has been attempted. Preserve two thirds for unseen names/retries while
    # guaranteeing independent continuous/phase geometry measurement.
    reserve=min(budget//3,sum(bool(needs_geometry.get(t)) for t in ordered))
    geometry=[t for t in ordered if needs_geometry.get(t)][:reserve]
    reserved=set(geometry)
    remaining=[t for t in ordered if t not in reserved]
    chosen=geometry+remaining[:max(0,budget-len(geometry))]
    positions={ticker:i for i,ticker in enumerate(ordered)}
    return sorted(chosen,key=lambda ticker:positions[ticker])


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
            result["early_setup_policy_version"]=EARLY_SETUP_POLICY_VERSION
            if result.get("verified_prebreakout_setup"):
                result["verified_prebreakout_setup"]["marketCapUSD"]=cap_by_ticker[ticker]
                result["verified_prebreakout_setup"]["early_setup_policy_version"]=EARLY_SETUP_POLICY_VERSION
            observed.append(result)
        except Exception as exc:
            observed.append({"ticker":ticker,"status":"provider_error",
                             "error_type":type(exc).__name__})
    evaluable=sum(x["status"]=="evaluable_ohlcv" for x in observed)
    technical_rejections=dict(sorted(Counter(
        x.get("technical_first_rejection","not_recorded_legacy")
        for x in observed if x["status"]=="evaluable_ohlcv").items()))
    attempt_status_counts=dict(sorted(Counter(x["status"] for x in observed).items()))
    provider_error_type_counts=dict(sorted(Counter(x["error_type"] for x in observed
        if x["status"]=="provider_error" and x.get("error_type")).items()))
    signals=[x["verified_prebreakout_setup"] for x in observed if x.get("verified_prebreakout_setup")]
    return {"schema":"vestra_breakout_lab_smallcap_ohlcv_research_v1",
            "early_setup_policy_version":EARLY_SETUP_POLICY_VERSION,
            "status":"observed_research_only_not_breakout_signals",
            "generated_at":checked_at.isoformat(),"source":"yfinance",
            "universe_100m_2b_count":len(names),
            "universe_cap_range_usd":[100_000_000,2_000_000_000],
            "universe_100m_500m_count":sum(1 for cap in (cap_by_ticker[t] for t in names)
                                            if type(cap) in (int,float) and cap<500_000_000),
            "universe_tickers_sha256":cohort_sha256,
            "universe_tickers":names,"slot":slot,"budget":budget,
            "provider_tickers_attempted":len(observed),
            "provider_attempt_status_counts":attempt_status_counts,
            "provider_error_type_counts":provider_error_type_counts,
            "evaluable_ohlcv":evaluable,"observed_incomplete":len(observed)-evaluable,
            "technical_first_rejection_counts":technical_rejections,
            "technical_structure_audit":technical_structure_audit(observed),
            "independent_geometry_audit":independent_geometry_audit(observed),
            "phase_robustness_audit":phase_robustness_audit(observed),
            "swing_geometry_audit":swing_geometry_audit(observed),
            "technical_evidence_audit":technical_evidence_audit(observed),
            "cohort_churn_audit":cohort_churn_audit({"universe_tickers":names},previous,observed),
            "not_observed":len(names)-len(observed),
            "universe_coverage_pct":round(100*evaluable/len(names),2) if names else None,
            "point_in_time_caveat":"market_caps_from_current_index_not_historical_asof_snapshots",
            "not_breakout_candidates":True,"no_success_probability":True,
            "validated_prebreakout_setups":len(signals),"signals":signals,
            "geometry_watch_observations":geometry_watch_observations(observed,checked_at),
            "swing_watch_observations":swing_watch_observations(observed),
            "observations":observed}


def merge_slots(current, previous, now, ttl_hours=96, *, eligible_tickers=None):
    """Merge only recent, independently collected OHLCV. Never revive stale setups."""
    from datetime import timedelta
    if not isinstance(previous,dict) or previous.get("schema")!=current.get("schema"):
        return current
    cutoff=now-timedelta(hours=ttl_hours)
    eligible=set(eligible_tickers) if eligible_tickers is not None else None
    count=current.get("universe_100m_2b_count",current.get("universe_100m_500m_count")) or 0
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
    previous_policy_setups_excluded=0
    for row in all_rows:
        setup=row.get("verified_prebreakout_setup")
        if row.get("status")!="evaluable_ohlcv" or not isinstance(setup,dict):
            continue
        if (row.get("early_setup_policy_version")!=EARLY_SETUP_POLICY_VERSION or
            setup.get("early_setup_policy_version")!=EARLY_SETUP_POLICY_VERSION):
            previous_policy_setups_excluded+=1
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
    technical_rejections=dict(sorted(Counter(
        row.get("technical_first_rejection","not_recorded_legacy")
        for row in all_rows if row.get("status")=="evaluable_ohlcv").items()))
    return {**current,"observations":all_rows,"signals":signals,
            "evaluable_ohlcv":evaluable,"observed_incomplete":len(all_rows)-evaluable,
            "technical_first_rejection_counts":technical_rejections,
            "technical_structure_audit":technical_structure_audit(all_rows),
            "independent_geometry_audit":independent_geometry_audit(all_rows),
            "phase_robustness_audit":phase_robustness_audit(all_rows),
            "swing_geometry_audit":swing_geometry_audit(all_rows),
            "technical_evidence_audit":technical_evidence_audit(all_rows),
            "cohort_churn_audit":cohort_churn_audit(current,previous,all_rows),
            "not_observed":max(0,count-len(all_rows)),
            "universe_coverage_pct":round(100*evaluable/count,2) if count else None,
            "validated_prebreakout_setups":len(signals),
            "geometry_watch_observations":geometry_watch_observations(all_rows,now),
            "swing_watch_observations":swing_watch_observations(all_rows),
            "setup_verification_window_hours":18,
            "historical_setups_excluded_as_stale":historical_setups_excluded,
            "previous_policy_setups_excluded":previous_policy_setups_excluded,
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
