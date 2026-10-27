#!/usr/bin/env python3
"""Forward cohorts based only on immutable, originally published scanner slots.

A ticker's first publication per stage defines one research cohort. Repeated
scans of the same stage never inflate sample size. No backfilled signals.
Price histories are supplied independently; missing prices remain missing.
"""
from __future__ import annotations
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from prebreakout_forward_evaluation import evaluate_archived
from prebreakout_stage_evidence import report
from prebreakout_forward_events import breakout_event
from prebreakout_research_features import research_features

STAGES={"compressão","pré-breakout","confirmado"}

def base_maturity(case:dict)->str:
    """Published age in calendar days; never mislabel elapsed days as market sessions."""
    anchor=case.get("base_start_date")
    if not anchor:
        return "unverified"
    days=(datetime.fromisoformat(case["signal_date"]).date()-
          datetime.fromisoformat(anchor).date()).days
    if days<0:
        return "unverified"
    if days<28:
        return "young_under_28d"
    if days<=84:
        return "developing_28_to_84d"
    return "extended_over_84d"


def wilson_interval(successes:int, total:int, z:float=1.959963984540054)->dict|None:
    """Two-sided 95% Wilson score interval; descriptive, not a forecast."""
    if type(successes) is not int or type(total) is not int or total<=0 or not 0<=successes<=total:
        return None
    p=successes/total
    denom=1+z*z/total
    centre=(p+z*z/(2*total))/denom
    radius=z*math.sqrt(p*(1-p)/total+z*z/(4*total*total))/denom
    return {"lower":round(max(0,centre-radius),4),
            "upper":round(min(1,centre+radius),4)}

def maturity_event_evidence(events:list[dict],cases:list[dict])->dict:
    """Transparent sample counts, no fitted probabilities or invented labels."""
    groups={}
    for case in cases:
        group=base_maturity(case)
        groups.setdefault(group,{"cohorts":0,"by_horizon":{str(h):{"confirmed":0,"not_confirmed":0,"pending_or_unverified":0} for h in (5,10,20)}})
        groups[group]["cohorts"]+=1
    for event in events:
        group=event["base_maturity"]
        bucket=groups[group]["by_horizon"][str(event["horizon_sessions"])]
        status=event["status"]
        if status in ("confirmed","not_confirmed"):
            bucket[status]+=1
            if status=="confirmed" and event.get("horizon_matured") is True:
                bucket["matured_confirmed"]=bucket.get("matured_confirmed",0)+1
        else:
            bucket["pending_or_unverified"]+=1
    for group in groups.values():
        for bucket in group["by_horizon"].values():
            bucket["evaluable"]=bucket["confirmed"]+bucket["not_confirmed"]
            bucket["breakout_probability"]=None
            # Descriptive interval only once sufficient COMPLETE horizons and
            # coverage exist. Early-confirmed immature cohorts are excluded.
            complete=bucket.get("matured_confirmed",0)+bucket["not_confirmed"]
            coverage=complete/group["cohorts"] if group["cohorts"] else 0
            bucket["matured_evaluable"]=complete
            bucket["matured_coverage"]=round(coverage,4)
            bucket["observed_breakout_fraction"]=round(bucket.get("matured_confirmed",0)/complete,4) if complete>=30 and coverage>=.8 else None
            bucket["wilson_95_descriptive"]=wilson_interval(bucket.get("matured_confirmed",0),complete) if complete>=30 and coverage>=.8 else None
            bucket["evidence_ready"]=complete>=30 and coverage>=.8
            # Event observations may share both ticker and market date.
            # A binomial Wilson interval assumes independent trials; its
            # publication must abstain when that condition is unverified.
            bucket["independence_verified"]=False
            bucket["wilson_95_descriptive"]=None
            bucket["evidence_ready"]=False
            bucket["independence_reason"]="correlated_ticker_and_market_cohorts_not_adjusted"
    return {"age_unit":"calendar_days","historical_only":True,
            "probability_calibrated":False,"minimum_matured_n":30,"minimum_matured_coverage":0.8,
            "interval_method":"wilson_95_withheld_until_dependence_robust_validation","groups":groups}


def purged_walkforward_folds(cases:list[dict], test_days:int=28, embargo_days:int=42)->dict:
    """Chronological research folds; calendar embargo is a proxy, not a verified exchange-session purge.

    No future outcomes are consulted to choose folds. A fold is a split plan,
    not a backtest or measured out-of-sample improvement.
    """
    from datetime import date, timedelta
    if type(test_days) is not int or type(embargo_days) is not int or test_days<1 or embargo_days<42:
        raise ValueError("invalid temporal split or insufficient embargo")
    ordered=sorted(cases,key=lambda c:(c["published_at"],c["ticker"],c["stage"]))
    days=[date.fromisoformat(c["published_at"][:10]) for c in ordered]
    if not days:
        return {"method":"purged_calendar_walkforward","folds":[],"out_of_sample_validated":False}
    first=min(days)
    last=max(days)
    folds=[]
    boundary=first+timedelta(days=test_days)
    while boundary<=last:
        stop=boundary+timedelta(days=test_days)
        train=[i for i,d in enumerate(days) if d < boundary-timedelta(days=embargo_days)]
        test=[i for i,d in enumerate(days) if boundary<=d<stop]
        if train and test:
            train_tickers={ordered[i]["ticker"] for i in train}
            test_tickers={ordered[i]["ticker"] for i in test}
            folds.append({"train_before":(boundary-timedelta(days=embargo_days)).isoformat(),
                          "test_from":boundary.isoformat(),"test_until_exclusive":stop.isoformat(),
                          "train_cohorts":len(train),"test_cohorts":len(test),
                          "repeated_issuers_across_sides":len(train_tickers & test_tickers),
                          "outcomes_computed":False})
        boundary=stop
    return {"method":"purged_calendar_walkforward",
            "embargo_calendar_days":embargo_days,"test_calendar_days":test_days,
            "out_of_sample_validated":False,"folds":folds}

def walkforward_holdout_returns(cases:list[dict], outcomes:list[dict], plan:dict, cost_bps:int=20)->dict:
    """Descriptive fold test outcomes only. No model fit, tuning, or alpha inference."""
    from datetime import date
    if len(cases)!=len(outcomes) or type(cost_bps) is not int or not 0<=cost_bps<=1000:
        raise ValueError("misaligned cohorts or invalid scenario cost")
    rows=[]
    for fold in plan["folds"]:
        lo=date.fromisoformat(fold["test_from"])
        hi=date.fromisoformat(fold["test_until_exclusive"])
        selected=[outcomes[i] for i,case in enumerate(cases)
                  if lo<=date.fromisoformat(case["published_at"][:10])<hi]
        horizons={}
        for h in (5,10,20):
            available=[]
            for result in selected:
                metric=result.get("results",{}).get(h)
                if not isinstance(metric,dict):
                    continue
                try:
                    gross=float(metric["return"])
                    bench=float(metric["spy_return"])
                    excess=float(metric["excess_return"])
                except (KeyError,ValueError,TypeError):
                    continue
                if not all(math.isfinite(v) for v in (gross,bench,excess)):
                    continue
                # The excess return must agree with its independently supplied
                # asset and benchmark components, otherwise abstain.
                if abs(excess-(gross-bench))>1e-8:
                    continue
                available.append((gross,bench,excess))
            n=len(available)
            horizons[str(h)]={
                "test_cohorts":len(selected),"evaluated":n,"missing":len(selected)-n,
                "coverage":round(n/len(selected),4) if selected else None,
                "mean_gross_return":round(sum(x[0] for x in available)/n,6) if n else None,
                "mean_spy_return":round(sum(x[1] for x in available)/n,6) if n else None,
                "mean_excess_after_scenario_cost":round(
                    sum(x[2]-cost_bps/10000 for x in available)/n,6) if n else None,
                "net_excess_positive":sum(x[2]>cost_bps/10000 for x in available),
                "net_excess_nonpositive":sum(x[2]<=cost_bps/10000 for x in available),
                "net_excess_hit_fraction_descriptive":round(
                    sum(x[2]>cost_bps/10000 for x in available)/n,4) if n else None,
                "outperformance_probability":None}
        rows.append({"test_from":fold["test_from"],"test_until_exclusive":fold["test_until_exclusive"],
                     "by_horizon":horizons})
    return {"method":"descriptive_chronological_holdout_adjusted_close",
            "cost_scenario_round_trip_bps":cost_bps,
            "cost_is_assumption":True,"executable_fills_verified":False,
            "out_of_sample_alpha_validated":False,"dependence_adjusted":False,
            "folds":rows}

def spy_regime_at_publication(published_at:str, benchmark_bars:list[dict])->str:
    """Use 21 strictly prepublication SPY closes; no current/future close."""
    from datetime import date
    try:
        cutoff=date.fromisoformat(published_at[:10])
        valid={}
        for bar in benchmark_bars:
            day=date.fromisoformat(str(bar["date"])[:10])
            close=float(bar["close"])
            if day>=cutoff or not math.isfinite(close) or close<=0 or day in valid:
                continue
            valid[day]=close
        rows=sorted(valid.items())
        if len(rows)<21:
            return "unknown"
        # Do not claim a 20-session regime on stale history.
        if (cutoff-rows[-1][0]).days>5:
            return "unknown"
        return "positive_spy_20d" if rows[-1][1]>rows[-21][1] else "nonpositive_spy_20d"
    except (KeyError,TypeError,ValueError,OverflowError):
        return "unknown"

def market_regime_audit(cases:list[dict], outcomes:list[dict], cost_bps:int=20)->dict:
    """Point-in-time regime proxy from an observed, earlier SPY return.
    
    Missing regime observations remain unknown. This is descriptive only:
    no fitted filter and no claim that a regime predicts future alpha.
    """
    from datetime import date
    if len(cases)!=len(outcomes):
        raise ValueError("cases and outcomes must be aligned")
    groups={name:{"cohorts":0,"by_horizon":{str(h):{"evaluable":0,"positive_net_excess":0,
        "missing":0} for h in (5,10,20)}} for name in ("positive_spy_20d","nonpositive_spy_20d","unknown")}
    for case,outcome in zip(cases,outcomes):
        label=case.get("market_regime_at_publication","unknown")
        if label not in groups:
            label="unknown"
        bucket=groups[label]
        bucket["cohorts"]+=1
        for h in (5,10,20):
            cell=bucket["by_horizon"][str(h)]
            row=outcome.get("results",{}).get(h)
            if not isinstance(row,dict):
                cell["missing"]+=1
                continue
            try:
                gross=float(row["return"]); spy=float(row["spy_return"]); excess=float(row["excess_return"])
            except (TypeError,ValueError,KeyError):
                cell["missing"]+=1
                continue
            if not all(math.isfinite(x) for x in (gross,spy,excess)) or abs(excess-(gross-spy))>1e-8:
                cell["missing"]+=1
                continue
            cell["evaluable"]+=1
            cell["positive_net_excess"]+=int(excess>cost_bps/10000)
    return {"method":"retrospective_stratification_no_predictive_claim",
            "regime_definition":"SPY 20 completed prepublication sessions; unavailable=>unknown",
            "probability_calibrated":False,"groups":groups}

def cohorts(archive:Path)->list[dict]:
    eligible=[]
    for path in archive.glob("*/slots/*-slot*.json"):
        try:
            data=json.loads(path.read_text(encoding="utf-8"))
            stamp=datetime.fromisoformat(str(data["generated_at"]).replace("Z","+00:00"))
            if stamp.tzinfo is None or data.get("schema")!="vestra_prebreakout_v1":continue
            stamp=stamp.astimezone(timezone.utc)
            slot=data.get("scan_slot_utc")
            if type(slot) is not int or slot!=stamp.hour//6:continue
            if path.name!=f"{stamp.date().isoformat()}-slot{slot}.json":continue
            if not isinstance(data.get("signals"),list):continue
            eligible.append((stamp,path.name,data))
        except (OSError,KeyError,TypeError,ValueError):
            continue
    selected={}
    for stamp,name,data in sorted(eligible,key=lambda x:(x[0],x[1])):
        counts={}
        for row in data["signals"]:
            if not isinstance(row,dict):continue
            ticker=str(row.get("ticker") or "").strip().upper()
            if not ticker or row.get("stage") not in STAGES or row.get("source")!="yahoo:daily_ohlcv":continue
            counts[ticker]=counts.get(ticker,0)+1
        for row in data["signals"]:
            if not isinstance(row,dict):continue
            ticker=str(row.get("ticker") or "").strip().upper()
            stage=row.get("stage")
            if not ticker or counts.get(ticker)!=1 or stage not in STAGES or row.get("source")!="yahoo:daily_ohlcv":continue
            try:
                date=datetime.fromisoformat(str(row["date"])[:10]).date()
            except (ValueError,TypeError,KeyError):continue
            if date>stamp.date():continue
            # Point-in-time base identity: never combine two independently
            # published bases merely because the ticker/stage is the same.
            # Legacy publications lacking an explicit base start remain on
            # the old ticker/stage policy; do not retroactively invent bases.
            anchor=row.get("baseStartDate")
            if anchor is not None:
                try:
                    base_date=datetime.fromisoformat(str(anchor)).date()
                except (TypeError,ValueError):
                    continue
                if base_date>date or (date-base_date).days>365:
                    continue
                anchor=base_date.isoformat()
            key=(ticker,stage,anchor)
            if key not in selected:
                selected[key]={"ticker":ticker,"stage":stage,
                    "base_start_date":anchor,
                    "published_at":stamp.isoformat(),"signal_date":date.isoformat(),
                    "snapshot":data}
    return [selected[k] for k in sorted(selected,key=lambda key:(selected[key]["published_at"],key))]

def structural_shadow_evidence(selected:dict, event_prices:dict|None)->dict:
    """Prospective shadow-vs-outcome counts, never a fitted probability.

    Include unknown diagnostics in the denominator. Event evaluability is
    independent of eligibility: missing/adjusted price bases remain unknown.
    """
    labels=("research_eligible","research_rejected","unverifiable")
    groups={label:{"cohorts":0,"by_horizon":{str(h):{"confirmed_matured":0,
        "not_confirmed_matured":0,"unverified_or_pending":0} for h in (5,10,20)}}
        for label in labels}
    for stamp,row in selected.values():
        shadow=row.get("structural_readiness_shadow")
        status=shadow.get("status") if isinstance(shadow,dict) and shadow.get("model")=="atr_support_v1_shadow" else None
        label=status if status in ("research_eligible","research_rejected") and type(shadow.get("eligible")) is bool and shadow["eligible"]==(status=="research_eligible") else "unverifiable"
        group=groups[label]
        group["cohorts"]+=1
        snapshot={"schema":"vestra_prebreakout_v1","generated_at":stamp.isoformat(),"signals":[row]}
        bars=(event_prices or {}).get(row["ticker"])
        for horizon in (5,10,20):
            cell=group["by_horizon"][str(horizon)]
            try:
                result=breakout_event(snapshot,row["ticker"],bars,horizon) if isinstance(bars,list) else {}
            except (KeyError,ValueError,TypeError,OverflowError):
                result={}
            if result.get("horizon_matured") is True and result.get("status") in ("confirmed","not_confirmed"):
                cell[result["status"]+"_matured"]+=1
            else:
                cell["unverified_or_pending"]+=1
    for group in groups.values():
        for cell in group["by_horizon"].values():
            valid=cell["confirmed_matured"]+cell["not_confirmed_matured"]
            cell["matured_evaluable"]=valid
            cell["observed_breakout_fraction_descriptive"]=round(cell["confirmed_matured"]/valid,4) if valid else None
            cell["matured_coverage"]=round(valid/group["cohorts"],4) if group["cohorts"] else None
            cell["minimum_evidence_met"]=valid>=30 and group["cohorts"]>0 and valid/group["cohorts"]>=.8
            cell["probability_calibrated"]=False
    return {"method":"prospective_structural_readiness_v1_asof_archived_shadow",
            "historical_only":True,"selection_effect_validated":False,
            "out_of_sample_validated":False,"success_probability":None,
            "groups":groups}


def shadow_forward_comparison(archive:Path, event_prices:dict|None)->dict:
    """Compare first prospectively archived shadow observations, not reconstructed signals.

    Rolling baseStartDate is NOT an independent episode identifier: conservative
    one-per-ticker-and-stage policy avoids daily pseudo-replication.
    """
    selected={}
    for path in sorted(archive.glob("*/slots/*-slot*.json")):
        try:
            data=json.loads(path.read_text(encoding="utf-8"))
            stamp=datetime.fromisoformat(str(data["generated_at"]).replace("Z","+00:00"))
            if stamp.tzinfo is None or data.get("schema")!="vestra_prebreakout_v1":
                continue
            stamp=stamp.astimezone(timezone.utc)
            slot=data.get("scan_slot_utc")
            if type(slot) is not int or slot!=stamp.hour//6 or path.name!=f"{stamp.date().isoformat()}-slot{slot}.json":
                continue
            shadow=data.get("quality_shadow_cases")
            if not isinstance(shadow,dict) or not isinstance(shadow.get("records"),list):
                continue
            seen=set()
            for row in shadow["records"]:
                if not isinstance(row,dict):
                    continue
                ticker=row.get("ticker");stage=row.get("stage")
                key=(ticker,stage)
                if not isinstance(ticker,str) or not ticker or stage not in STAGES or key in seen:
                    continue
                seen.add(key)
                if row.get("legacy_eligible") is not True or type(row.get("strict_eligible")) is not bool:
                    continue
                if row.get("source")!="yahoo:daily_ohlcv" or row.get("signalPriceBasis")!="yahoo_auto_adjusted_asof_publication":
                    continue
                if key not in selected or stamp<selected[key][0]:
                    selected[key]=(stamp,row)
        except (OSError,ValueError,TypeError,KeyError):
            continue
    groups={g:{"cohorts":0,"by_horizon":{str(h):{"confirmed_matured":0,"not_confirmed_matured":0,"unverified_or_pending":0,"durability":{str(w):{"observed":0,"held_pivot":0,"lost_pivot":0,"pending_or_unverified":0,"sum_end_return":0.0,"positive":0,"nonpositive":0,"gross_gain_sum":0.0,"gross_loss_abs_sum":0.0,"held_positive":0,"held_nonpositive":0,"lost_positive":0,"lost_nonpositive":0} for w in (3,5,10)}}
        for h in (5,10,20)}} for g in ("passed_strict","rejected_strict")}
    for stamp,row in selected.values():
        group=groups["passed_strict" if row["strict_eligible"] else "rejected_strict"]
        group["cohorts"]+=1
        snapshot={"schema":"vestra_prebreakout_v1","generated_at":stamp.isoformat(),"signals":[row]}
        bars=(event_prices or {}).get(row["ticker"])
        for h in (5,10,20):
            cell=group["by_horizon"][str(h)]
            try:
                result=breakout_event(snapshot,row["ticker"],bars,h) if isinstance(bars,list) else {}
            except (ValueError,KeyError,TypeError,OverflowError):
                result={}
            if result.get("horizon_matured") is True and result.get("status")=="confirmed":
                cell["confirmed_matured"]+=1
                durability=result.get("durability",{})
                for w in (3,5,10):
                    tally=cell["durability"][str(w)]
                    observation=durability.get(str(w)) if isinstance(durability,dict) else None
                    if (isinstance(observation,dict) and observation.get("status")=="observed"
                        and type(observation.get("held_pivot")) is bool):
                        tally["observed"]+=1
                        tally["held_pivot" if observation["held_pivot"] else "lost_pivot"]+=1
                        try:
                            ret=float(observation["end_return_from_breakout"])
                        except (KeyError,ValueError,TypeError):
                            pass
                        else:
                            if math.isfinite(ret):
                                tally["sum_end_return"]+=ret
                                tally["positive" if ret>0 else "nonpositive"]+=1
                                tally[("held" if observation["held_pivot"] else "lost")+("_positive" if ret>0 else "_nonpositive")]+=1
                                if ret>0:tally["gross_gain_sum"]+=ret
                                elif ret<0:tally["gross_loss_abs_sum"]-=ret
                    else:
                        tally["pending_or_unverified"]+=1
            elif result.get("horizon_matured") is True and result.get("status")=="not_confirmed":
                cell["not_confirmed_matured"]+=1
            else:
                cell["unverified_or_pending"]+=1
    for group in groups.values():
        for cell in group["by_horizon"].values():
            complete=cell["confirmed_matured"]+cell["not_confirmed_matured"]
            total=group["cohorts"]
            cell["matured_evaluable"]=complete
            cell["matured_coverage"]=round(complete/total,4) if total else None
            cell["observed_breakout_fraction"]=round(cell["confirmed_matured"]/complete,4) if complete else None
            cell["observed_fraction_is_probability"]=False
            cell["minimum_evidence_met"]=complete>=30 and total>0 and complete/total>=.8
            cell["selection_effect_validated"]=False
            for tally in cell["durability"].values():
                n=tally["positive"]+tally["nonpositive"]
                tally["return_evaluable"]=n
                tally["joint_outcome_evaluable"]=n
                tally["joint_outcome_missing_return"]=tally["observed"]-n
                tally["joint_outcome_coverage"]=round(n/tally["observed"],4) if tally["observed"] else None
                tally["joint_outcome_counts_consistent"]=(n==sum(tally[k] for k in ("held_positive","held_nonpositive","lost_positive","lost_nonpositive")))
                tally["joint_outcome_fraction_descriptive"]=(round(tally["held_positive"]/n,4) if n else None)
                tally["joint_outcome_fraction_is_probability"]=False
                tally["joint_outcome_definition"]="pivot_state_at_window_x_positive_end_return_from_breakout"
                tally["mean_end_return_from_breakout"]=round(tally["sum_end_return"]/n,6) if n else None
                tally["gain_loss_ratio_descriptive"]=(round(tally["gross_gain_sum"]/tally["gross_loss_abs_sum"],4)
                    if tally["gross_loss_abs_sum"]>0 else None)
                tally["payoff_probability_calibrated"]=False
                del tally["sum_end_return"]
                del tally["gross_gain_sum"]
                del tally["gross_loss_abs_sum"]
    return {"method":"prospective_first_publication_ticker_stage_no_rolling_base_dedup",
            "historical_only":True,"success_probability":None,
            "statistically_validated":False,"groups":groups,
            "structural_readiness_evidence":structural_shadow_evidence(selected,event_prices)}

def retrospective_feature_outcome_audit(cases:list[dict], events:list[dict], prices:dict, benchmark_bars:list[dict])->dict:
    """Pair prepublication features with matured outcomes, no model fit."""
    lookup={(r["ticker"],r["stage"],r["published_at"],r["horizon_sessions"]):r for r in events}
    result={"method":"retrospective_asof_features_vs_archived_events",
            "historical_only":True,"trained_model":False,"predictive_validity_established":False,
            "adjusted_history_point_in_time_verified":False,"records":[]}
    for case in cases:
        features=research_features(prices.get(case["ticker"]),benchmark_bars,case["published_at"])
        for horizon in (5,10,20):
            event=lookup.get((case["ticker"],case["stage"],case["published_at"],horizon),{})
            matured=event.get("horizon_matured") is True
            status=event.get("status") if matured and event.get("status") in ("confirmed","not_confirmed") else "pending_or_unverified"
            durability=event.get("durability") if status=="confirmed" else None
            joint={}
            for window in (3,5,10,20):
                obs=durability.get(str(window)) if isinstance(durability,dict) else None
                label="pending_or_unverified"
                if (isinstance(obs,dict) and obs.get("status")=="observed"
                    and type(obs.get("held_pivot")) is bool):
                    try:
                        end_ret=float(obs["end_return_from_breakout"])
                    except (KeyError,ValueError,TypeError):
                        pass
                    else:
                        if math.isfinite(end_ret):
                            label=("held" if obs["held_pivot"] else "lost")+("_positive" if end_ret>0 else "_nonpositive")
                joint[str(window)]=label
            result["records"].append({"ticker":case["ticker"],"stage":case["stage"],
                "published_at":case["published_at"],"horizon_sessions":horizon,
                "outcome":status,"joint_durability_outcomes":joint,"features":features["features"],
                "feature_missing":features["missing"],"features_point_in_time_verified":False})
    return result

def benchmark_followthrough(bars:list[dict]|None, event_date:str|None, window:int)->float|None:
    """Exact anchor, ordered positive SPY closes, complete forward sessions."""
    if not isinstance(bars,list) or not event_date or type(window) is not int or window<1: return None
    try:
        dates=[date.fromisoformat(str(row["date"])[:10]) for row in bars]
        closes=[float(row["close"]) for row in bars]
        anchor=date.fromisoformat(event_date)
    except (KeyError,ValueError,TypeError,OverflowError): return None
    if any(not math.isfinite(p) or p<=0 for p in closes): return None
    if any(dates[i]>=dates[i+1] for i in range(len(dates)-1)) or dates.count(anchor)!=1: return None
    i=dates.index(anchor)
    if i+window>=len(closes): return None
    if any(dates[k]-dates[k-1]>timedelta(days=7) for k in range(i+1,i+window+1)): return None
    return closes[i+window]/closes[i]-1

def daily_focus_forward_evidence(archive:Path, event_prices:dict|None=None, benchmark_bars:list[dict]|None=None)->dict:
    """Measure the actual archived daily featured pick, not a hindsight winner.

    One earliest valid selection per UTC day. No invented selection for a
    day without an immutable archive, and no reuse of a carried old signal.
    """
    selected={}; archive_days=set(); explicit_abstention_days=set(); invalid_focus_days=set(); candidate_publication_days=set()
    for path in sorted(archive.glob("*/slots/*-slot*.json")):
        try:
            feed=json.loads(path.read_text(encoding="utf-8"))
            stamp=datetime.fromisoformat(str(feed["generated_at"]).replace("Z","+00:00"))
            if stamp.tzinfo is None or feed.get("schema")!="vestra_prebreakout_v1":
                continue
            stamp=stamp.astimezone(timezone.utc)
            slot=feed.get("scan_slot_utc")
            if type(slot) is not int or slot!=stamp.hour//6 or path.name!=f"{stamp.date().isoformat()}-slot{slot}.json":
                continue
            day=stamp.date().isoformat()
            archive_days.add(day)
            focus=feed.get("daily_focus")
            if isinstance(focus,dict) and focus.get("status")=="no_qualified_setup":
                explicit_abstention_days.add(day)
                continue
            if not isinstance(focus,dict) or focus.get("status")!="research_candidate":
                invalid_focus_days.add(day)
                continue
            candidate_publication_days.add(day)
            ticker=focus.get("ticker")
            if not isinstance(ticker,str) or not ticker.strip():continue
            matches=[s for s in feed.get("signals",[]) if isinstance(s,dict) and
                     s.get("ticker")==ticker and s.get("stage") in ("pré-breakout","compressão") and
                     s.get("source")=="yahoo:daily_ohlcv"]
            if len(matches)!=1:continue
            row=matches[0]
            tier=focus.get("selection_tier")
            if tier not in ("verified_prebreakout","developing_setup",None):
                continue
            if tier=="verified_prebreakout" and row["stage"]!="pré-breakout":
                continue
            if tier=="developing_setup" and row.get("vcpConfirmed") is not True:
                continue
            # Historical publications without an explicit tier use the actual observed stage.
            tier=tier or ("verified_prebreakout" if row["stage"]=="pré-breakout" else "developing_setup")
            # The daily recommendation is only an independently measured
            # as-of selection if its original scan timestamp is available.
            verified=row.get("scanner_verified_at")
            if not isinstance(verified,str):continue
            scan=datetime.fromisoformat(verified.replace("Z","+00:00"))
            if scan.tzinfo is None or not 0 <= (stamp-scan.astimezone(timezone.utc)).total_seconds() <= 18*3600:continue
            if day not in selected or stamp<selected[day][0]:
                selected[day]=(stamp,row,tier)
        except (OSError,ValueError,KeyError,TypeError,AttributeError):
            continue
    results={str(h):{"selected":len(selected),"matured_confirmed":0,
        "matured_not_confirmed":0,"pending_or_unverifiable":0} for h in (5,10,20)}
    by_tier={tier:{"selected":0,"by_horizon":{str(h):{"matured_confirmed":0,
        "matured_not_confirmed":0,"pending_or_unverifiable":0} for h in (5,10,20)}}
        for tier in ("verified_prebreakout","developing_setup")}
    for group in by_tier.values():
        for cell in group["by_horizon"].values():
            cell["post_confirmation_payoff"]={str(w):{"confirmed":0,"completed":0,"pending_or_unverifiable":0,"positive_gross":0,"positive_net_after_20bp":0,"gross_sum":0.0,"net_sum":0.0,"benchmark_paired":0,"benchmark_missing":0,"excess_sum":0.0} for w in (3,5,10,20)}
    for stamp,row,tier in selected.values():
        by_tier[tier]["selected"]+=1
        snapshot={"schema":"vestra_prebreakout_v1","generated_at":stamp.isoformat(),"signals":[row]}
        prices=(event_prices or {}).get(row["ticker"])
        for horizon in (5,10,20):
            cell=results[str(horizon)]
            tier_cell=by_tier[tier]["by_horizon"][str(horizon)]
            try:
                event=breakout_event(snapshot,row["ticker"],prices,horizon) if isinstance(prices,list) else {}
            except (KeyError,ValueError,TypeError,OverflowError):
                event={}
            if event.get("horizon_matured") is True and event.get("status") in ("confirmed","not_confirmed"):
                cell["matured_"+event["status"]]+=1
                tier_cell["matured_"+event["status"]]+=1
                if event["status"]=="confirmed":
                    for window,payoff in tier_cell["post_confirmation_payoff"].items():
                        payoff["confirmed"]+=1
                        obs=event.get("durability",{}).get(window)
                        value=obs.get("end_return_from_breakout") if isinstance(obs,dict) and obs.get("status")=="observed" else None
                        if (isinstance(value,(float,int)) and not isinstance(value,bool)
                            and math.isfinite(value) and type(obs.get("held_pivot")) is bool):
                            payoff["completed"]+=1
                            payoff["positive_gross"]+=int(value>0)
                            payoff["positive_net_after_20bp"]+=int(value>0.002)
                            payoff["gross_sum"]+=value
                            payoff["net_sum"]+=value-0.002
                            benchmark=benchmark_followthrough(benchmark_bars,event.get("event_date"),int(window))
                            if benchmark is None: payoff["benchmark_missing"]+=1
                            else:
                                payoff["benchmark_paired"]+=1
                                payoff["excess_sum"]+=value-benchmark
                        else:
                            payoff["pending_or_unverifiable"]+=1
            else:
                cell["pending_or_unverifiable"]+=1
                tier_cell["pending_or_unverifiable"]+=1
    for cell in results.values():
        total=cell["matured_confirmed"]+cell["matured_not_confirmed"]
        cell["evaluable"]=total
        cell["matured_coverage"]=round(total/cell["selected"],4) if cell["selected"] else None
        cell["observed_confirmation_fraction"]=round(cell["matured_confirmed"]/total,4) if total else None
        cell["minimum_sample_met"]=total>=30 and cell["selected"]>0 and total/cell["selected"]>=.8
        cell["calibrated_probability"]=None
    for group in by_tier.values():
        for cell in group["by_horizon"].values():
            total=cell["matured_confirmed"]+cell["matured_not_confirmed"]
            cell["evaluable"]=total
            cell["matured_coverage"]=round(total/group["selected"],4) if group["selected"] else None
            cell["observed_confirmation_fraction"]=round(cell["matured_confirmed"]/total,4) if total else None
            cell["calibrated_probability"]=None
            for payoff in cell["post_confirmation_payoff"].values():
                n=payoff["completed"]
                payoff["mean_gross_return"]=round(payoff.pop("gross_sum")/n,6) if n else None
                payoff["mean_net_after_20bp"]=round(payoff.pop("net_sum")/n,6) if n else None
                paired=payoff["benchmark_paired"]
                payoff["mean_excess_vs_spy"]=round(payoff.pop("excess_sum")/paired,6) if paired else None
                payoff["benchmark_pair_coverage"]=round(paired/n,4) if n else None
                payoff["coverage_of_confirmed"]=round(n/payoff["confirmed"],4) if payoff["confirmed"] else None
                payoff["calibrated_probability"]=None
                payoff["execution_verified"]=False
                payoff["cost_scenario_round_trip_fraction"]=0.002
    return {"method":"first_archived_qualified_daily_focus_asof","archive_days":len(archive_days),
        "days_with_verifiable_daily_pick":len(selected),
        "days_without_verifiable_daily_pick":len(archive_days)-len(selected),
        "days_with_archived_candidate_publication":len(candidate_publication_days),
        "days_with_explicit_abstention_only":len((explicit_abstention_days-candidate_publication_days)),
        "days_with_invalid_or_missing_focus_publication":len(invalid_focus_days-candidate_publication_days-explicit_abstention_days),
        "days_with_candidate_but_no_verifiable_pick":len(candidate_publication_days-set(selected)),
        "historical_only":True,"out_of_sample_validated":False,"by_horizon":results,
        "by_selection_tier":by_tier}


def build(archive:Path,prices:dict,benchmark_bars:list[dict],event_prices:dict|None=None)->dict:
    cases=cohorts(archive)
    outcomes=[]
    for case in cases:
        bars=prices.get(case["ticker"])
        if not isinstance(bars,list) or not isinstance(benchmark_bars,list):
            outcome={"ticker":case["ticker"],"stage":case["stage"],"published_at":case["published_at"],
                     "signal_date":case["signal_date"],"entry":None,"results":{}}
        else:
            try:
                outcome=evaluate_archived(case["snapshot"],case["ticker"],bars,benchmark_bars)
            except (ValueError,TypeError,KeyError,ZeroDivisionError):
                outcome={"ticker":case["ticker"],"stage":case["stage"],"published_at":case["published_at"],
                         "signal_date":case["signal_date"],"entry":None,"results":{}}
        outcomes.append(outcome)
    events=[]
    for case in cases:
        rows=(event_prices or {}).get(case["ticker"])
        for horizon in (5,10,20):
            event={"ticker":case["ticker"],"stage":case["stage"],
                   "published_at":case["published_at"],"horizon_sessions":horizon,
                   "base_maturity":base_maturity(case)}
            if not isinstance(rows,list) or not rows:
                event.update({"status":"missing_ohlcv","observed_sessions":0,"event_date":None})
            else:
                try:
                    event.update(breakout_event(case["snapshot"],case["ticker"],rows,horizon))
                except (ValueError,KeyError,TypeError,OverflowError):
                    event.update({"status":"invalid_ohlcv","observed_sessions":0,"event_date":None})
            events.append(event)
    # Publish the denominator explicitly: pending/unverifiable cohorts are
    # never silently counted as breakouts that failed.
    event_coverage={}
    for horizon in (5,10,20):
        sample=[row for row in events if row["horizon_sessions"]==horizon]
        counts={}
        for row in sample:
            status=row["status"]
            counts[status]=counts.get(status,0)+1
        evaluated=counts.get("confirmed",0)+counts.get("not_confirmed",0)
        matured=sum(1 for row in sample if row.get("horizon_matured") is True)
        confirmed_early=sum(1 for row in sample if row["status"]=="confirmed" and row.get("horizon_matured") is False)
        # Durability is measured only where the post-confirmation horizon is complete.
        # A confirmed trigger is not automatically a durable success.
        durability={}
        for window in ("3","5","10","20"):
            observed=[row["durability"][window] for row in sample
                      if row["status"]=="confirmed" and
                      isinstance(row.get("durability"),dict) and
                      isinstance(row["durability"].get(window),dict) and
                      row["durability"][window].get("status")=="observed" and
                      type(row["durability"][window].get("held_pivot")) is bool]
            # Returns are observations from the confirmation close, not executable
            # orders. Apply an explicit round-trip cost scenario only to complete
            # durability windows. Do not count pending outcomes as losers.
            returns=[float(row["end_return_from_breakout"]) for row in observed
                     if isinstance(row.get("end_return_from_breakout"),(float,int))
                     and math.isfinite(float(row["end_return_from_breakout"]))]
            cost_fraction=0.002
            net=[ret-cost_fraction for ret in returns]
            durability[window]={"observed":len(observed),
                "held_pivot":sum(row["held_pivot"] for row in observed),
                "lost_pivot":sum(not row["held_pivot"] for row in observed),
                "return_observations":len(returns),
                "positive_gross":sum(value>0 for value in returns),
                "positive_net_after_cost_scenario":sum(value>0 for value in net),
                "mean_gross_return":round(sum(returns)/len(returns),6) if returns else None,
                "mean_net_return_scenario":round(sum(net)/len(net),6) if net else None,
                "cost_scenario_round_trip_fraction":cost_fraction,
                "execution_adjusted":False,
                "calibrated_probability":None}
        event_coverage[str(horizon)]={
            "cohorts":len(sample),"evaluable":evaluated,
            "matured_horizons":matured,"confirmed_before_maturity":confirmed_early,
            "post_confirmation_durability":durability,
            "coverage":round(evaluated/len(sample),4) if sample else None,
            "by_status":counts,"breakout_rate":None,
            "reason":"insufficient_or_unverified_forward_evidence"}
    # Operational diagnosis uses exactly one event per archived cohort at each
    # horizon. Never conflate a price reconciliation failure with no breakout.
    price_basis_audit={}
    for horizon in (5,10,20):
        sample=[row for row in events if row["horizon_sessions"]==horizon]
        causes={}
        for row in sample:
            if row.get("status")=="price_basis_unverified":
                reason=row.get("price_basis_diagnostic") or "legacy_unspecified"
                causes[reason]=causes.get(reason,0)+1
        price_basis_audit[str(horizon)]={"unverifiable":sum(causes.values()),
            "by_reason":causes,"price_factor_inferred":False,
            "counts_excluded_from_negative_outcomes":True}
    anchor_provenance={"verifiable_archived_price_basis":0,
        "legacy_missing_or_unverified_price_basis":0,
        "potentially_verifiable_by_horizon":{}}
    for case in cases:
        signal=next((row for row in case["snapshot"].get("signals",[])
                     if row.get("ticker")==case["ticker"]),{})
        try:
            price=float(signal.get("signalClose"))
            pivot=float(signal.get("resistance"))
            verified=(signal.get("signalPriceBasis")=="yahoo_auto_adjusted_asof_publication"
                      and math.isfinite(price) and price>0
                      and math.isfinite(pivot) and pivot>0)
        except (ValueError,TypeError,OverflowError):
            verified=False
        key="verifiable_archived_price_basis" if verified else "legacy_missing_or_unverified_price_basis"
        anchor_provenance[key]+=1
    for horizon in (5,10,20):
        sample=[event for event in events if event["horizon_sessions"]==horizon]
        anchor_provenance["potentially_verifiable_by_horizon"][str(horizon)]={
            "eligible_anchor_cohorts":anchor_provenance["verifiable_archived_price_basis"],
            "pending":sum(row["status"]=="pending" for row in sample),
            "evaluated":sum(row["status"] in ("confirmed","not_confirmed") for row in sample),
            "not_a_probability":True}
    return {"schema":"vestra_prebreakout_forward_cohorts_v1",
        "breakout_event_evidence":{"historical_only":True,"method":"published_pivot_future_ohlcv",
            "price_basis_audit":price_basis_audit,
            "unvalidated_probability":True,"coverage_by_horizon":event_coverage,"events":events},
        "evaluation_method":"adjusted_daily_close_after_publication",
        "cohort_policy":"first_immutable_publication_per_ticker_stage_and_verified_base_start",
        "historical_only":True,"cohort_count":len(cases),
        "anchor_provenance_audit":anchor_provenance,
        "base_identity_coverage":{"anchored":sum(case["base_start_date"] is not None for case in cases),
                                  "legacy_unanchored":sum(case["base_start_date"] is None for case in cases)},
        "base_maturity_evidence":maturity_event_evidence(events,cases),
        "market_regime_audit":market_regime_audit([{**case, "market_regime_at_publication":
            spy_regime_at_publication(case["published_at"],benchmark_bars)} for case in cases],outcomes),
        "walkforward_split_plan":purged_walkforward_folds(cases),
        "walkforward_holdout_returns":walkforward_holdout_returns(cases,outcomes,purged_walkforward_folds(cases)),
        "shadow_forward_comparison":shadow_forward_comparison(archive,event_prices),
        "daily_focus_forward_evidence":daily_focus_forward_evidence(archive,event_prices,benchmark_bars),
        "retrospective_feature_outcome_audit":retrospective_feature_outcome_audit(cases,events,prices,benchmark_bars),
        "stage_evidence":report(outcomes),"outcomes":outcomes}

if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--archive",type=Path,default=Path(__file__).resolve().parents[1]/"data/prebreakout-history")
    parser.add_argument("--prices",type=Path,required=True,help="JSON map ticker -> adjusted OHLCV bars, plus SPY benchmark")
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    prices=json.loads(args.prices.read_text(encoding="utf-8"))
    if not isinstance(prices,dict) or not isinstance(prices.get("SPY"),list):
        raise ValueError("require independent SPY adjusted daily benchmark")
    result=build(args.archive,prices,prices["SPY"],event_prices=prices)
    args.output.write_text(json.dumps(result,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
