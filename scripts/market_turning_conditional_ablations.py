#!/usr/bin/env python3
"""Stress-conditioned, paired chronological ablations (research only).

Outcome labels remain fixed, but only sessions already eligible by prior stress
enter evaluation. The preceding drawdown/run-up is *not* a predictor: it is a
necessary condition of the label and previously inflated unconditional skill.
All variants use identical as-of rows and test anchors; no cherry-picked sample
per factor. Reports are never calibrated live probabilities.
"""
from __future__ import annotations
from collections import defaultdict
from random import Random
from market_turning_feature_lab import feature_row, future_reversal_labels, series
from market_turning_walkforward import fit, predict, metrics, PURGE, FOLD, HORIZONS

KEYS = ("vix_percentile_126", "vix_1m_3m_ratio",
        "rsi_daily_5", "rsi_weekly_14", "mfi_daily_14",
        "hyg_lqd_change_5_pct")
GROUPS = {
    "volatility": ("vix_percentile_126", "vix_1m_3m_ratio"),
    "momentum": ("rsi_daily_5", "rsi_weekly_14"),
    "volume": ("mfi_daily_14",),
    "credit_price_proxy": ("hyg_lqd_change_5_pct",),
}
HORIZON = 10
MIN_ELIGIBLE_TRAIN = 150

def eligible_spy_sessions(spy, side, horizon=HORIZON):
    """Eligibility uses ONLY past and current closes, never future outcomes."""
    result = set()
    for i in range(125, len(spy)-horizon):
        previous = [row["close"] for row in spy[i-125:i+1]]
        last = previous[-1]
        eligible = (last <= max(previous)*.93 if side == "bottom"
                    else last >= min(previous)*1.07)
        if eligible:
            result.add(i)
    return result

def variants():
    return {"full": KEYS, **{
        "without_"+group: tuple(k for k in KEYS if k not in removed)
        for group, removed in GROUPS.items()}}

def year_block_brier_skill_ci(model_pairs, comparator_pairs, years, *, seed=1729, draws=800):
    """Paired calendar-year block resampling, with fixed research seed.

    Returns a descriptive 95% interval for 1-Brier(model)/Brier(comparator).
    Retains each year's correlated observations as a block. Annual blocks are
    not genuinely independent market crises; this does NOT validate calibration.
    """
    if len(model_pairs)!=len(comparator_pairs) or len(years)!=len(model_pairs):
        raise ValueError("paired forecasts and calendar blocks must align")
    blocks=defaultdict(list)
    for i,year in enumerate(years):
        blocks[int(year)].append(i)
    keys=sorted(blocks)
    if len(keys)<5 or len(model_pairs)<25:
        return {"available":False,"reason":"insufficient_calendar_blocks_or_anchors",
                "calendar_year_blocks":len(keys)}
    rng=Random(seed)
    skills=[]
    for _ in range(draws):
        sampled=[j for _ in keys for j in blocks[rng.choice(keys)]]
        numerator=sum((model_pairs[j][0]-model_pairs[j][1])**2 for j in sampled)
        denominator=sum((comparator_pairs[j][0]-comparator_pairs[j][1])**2 for j in sampled)
        if denominator>0:
            skills.append(1-numerator/denominator)
    if len(skills)<draws*.9:
        return {"available":False,"reason":"degenerate_brier_baseline",
                "calendar_year_blocks":len(keys)}
    skills.sort()
    quant=lambda q:round(skills[min(len(skills)-1,int((len(skills)-1)*q))],5)
    return {"available":True,"calendar_year_blocks":len(keys),
            "resamples":len(skills),"seed":seed,
            "percentile_95_ci":[quant(.025),quant(.975)],
            "fraction_resamples_positive":round(sum(v>0 for v in skills)/len(skills),4),
            "block_unit":"calendar_year_not_independent_crisis",
            "for_research_only_not_probability_calibration":True}

def stress_episode_groups(samples, *, max_gap_sessions=20):
    """Group stress-eligible anchors into episodes using only past timestamps.

    Gap is counted in SPY trading-session indices. A later eligible anchor
    starts a new block when more than 20 trading sessions passed since the
    preceding eligible observation. Do not label these independent crises.
    """
    blocks={}
    prior=None
    block=-1
    for item in samples:
        index=item["index"]
        if prior is not None and index<=prior:
            raise ValueError("eligible observations must be ordered and unique")
        if prior is None or index-prior>max_gap_sessions:
            block+=1
        blocks[index]=block
        prior=index
    return blocks


def episode_block_skill_ci(model_pairs, comparator_pairs, episode_ids, *, draws=800):
    """Paired bootstrap respecting clusters of nearby stressed sessions."""
    result=year_block_brier_skill_ci(model_pairs,comparator_pairs,episode_ids,
                                    seed=2718,draws=draws)
    result["stress_episode_blocks"]=result.pop("calendar_year_blocks")
    result["block_unit"]="consecutive_stress_eligibility_separated_by_more_than_20_sessions"
    result["episodes_are_not_proven_independent_market_crises"]=True
    return result


def conservative_research_gate(result):
    """Interpret confidence evidence; NEVER authorize live probabilities."""
    output={}
    for side in ("bottom","top"):
        row=result["results"][side]
        episodes=row["paired_stress_episode_bootstrap"]["full_vs_baseline"]
        years=row["paired_year_block_bootstrap"]["full_vs_baseline"]
        sample=row["models"]["full"] or {}
        checks={
            "minimum_30_positive_labels":sample.get("events",0)>=30,
            "minimum_80_nonoverlap_anchors":sample.get("n_nonoverlapping_test_anchors",0)>=80,
            "minimum_12_stress_episode_blocks":episodes.get("stress_episode_blocks",0)>=12,
            "year_block_ci_excludes_zero":years.get("available") is True and
                years["percentile_95_ci"][0]>0,
            "stress_episode_ci_excludes_zero":episodes.get("available") is True and
                episodes["percentile_95_ci"][0]>0,
            "original_point_in_time_vintages_verified":False,
            "independent_prospective_outcomes_verified":False,
        }
        output[side]={
            "descriptive_consistency_checks":checks,
            "historical_consistency_observed":all(v for k,v in checks.items()
                                                 if k not in (
                                                   "original_point_in_time_vintages_verified",
                                                   "independent_prospective_outcomes_verified")),
            "live_probability_authorized":False,
            "promotion_blockers":[k for k,v in checks.items() if not v],
            "interpretation":"historical_study_not_a_live_signal",
        }
    return output


def conditional_evaluate(raw):
    hist = {key: series(raw,key) for key in
            ("SPY", "^VIX", "^VVIX", "^COR1M", "^VIX3M", "HYG", "LQD")}
    spy=hist["SPY"]
    if len(spy) < 1500:
        return {"evaluated": False, "reason":"insufficient_history"}
    # Compute all as-of features once, only on completed days.
    observations = []
    for i in range(125,len(spy)-HORIZON):
        feats=feature_row(hist,spy[i]["date"])
        if feats is not None and all(feats[k] is not None for k in KEYS):
            observations.append({"index":i,"date":spy[i]["date"],"features":feats})
    report={}
    for side in ("bottom","top"):
        eligible=eligible_spy_sessions(spy,side)
        samples=[]
        for item in observations:
            if item["index"] not in eligible: continue
            label=future_reversal_labels(spy,item["index"],forward=HORIZON,nearby=5)[side]
            if label is None: continue
            samples.append({**item,"label":int(label)})
        episode_lookup=stress_episode_groups(samples)
        by_model={name:[] for name in variants()}
        baseline=[]
        anchor_years=[]
        anchor_episodes=[]
        folds=[]
        # Fold boundaries are calendar trading sessions, not count of
        # stressed observations; thus no event-selected time warping.
        for start_index in range(125+1008,len(spy)-HORIZON,FOLD):
            finish=min(start_index+FOLD,len(spy)-HORIZON)
            train=[row for row in samples if row["index"] < start_index-PURGE-HORIZON]
            test=[row for row in samples if start_index<=row["index"]<finish]
            if len(train)<MIN_ELIGIBLE_TRAIN:continue
            fitted={name:fit(train,keys) for name,keys in variants().items()}
            if any(model is None for model in fitted.values()):continue
            independent=[]
            last=-100000
            for row in test:
                if row["index"]-last<HORIZON:continue
                independent.append(row)
                last=row["index"]
            if not independent:continue
            prevalence=sum(x["label"] for x in train)/len(train)
            for row in independent:
                baseline.append((prevalence,row["label"]))
                anchor_years.append(int(row["date"][:4]))
                anchor_episodes.append(episode_lookup[row["index"]])
                for name,keys in variants().items():
                    by_model[name].append((predict(fitted[name],row["features"],keys),row["label"]))
            folds.append({"start":independent[0]["date"],"end":independent[-1]["date"],
                          "eligible_train":len(train),"test_anchors":len(independent)})
        base=metrics(baseline)
        scores={k:metrics(v) for k,v in by_model.items()}
        full=scores["full"]
        report[side]={
            "eligible_asof_rows_with_common_complete_features":len(samples),
            "folds":folds,"baseline":base,"models":scores,
            "incremental_family_brier_skill":{
                group:round(1-full["brier"]/scores["without_"+group]["brier"],5)
                if full and scores["without_"+group] and scores["without_"+group]["brier"] else None
                for group in GROUPS},
            "full_vs_conditional_training_prevalence_brier_skill":
                round(1-full["brier"]/base["brier"],5)
                if full and base and base["brier"] else None,
            "all_variants_identical_out_of_sample_anchors":True,
            "paired_stress_episode_bootstrap":{"full_vs_baseline":
                episode_block_skill_ci(by_model["full"],baseline,anchor_episodes),
                "incremental_by_family":{
                    group:episode_block_skill_ci(
                        by_model["full"],by_model["without_"+group],anchor_episodes)
                    for group in GROUPS}},
            "paired_year_block_bootstrap":{"full_vs_baseline":
                year_block_brier_skill_ci(by_model["full"],baseline,anchor_years),
                "incremental_by_family":{
                    group:year_block_brier_skill_ci(by_model["full"],by_model["without_"+group],anchor_years)
                    for group in GROUPS}},
        }
    output={"schema":"vestra_stress_conditioned_ablation_research_v2",
            "evaluated":True,"research_only":True,"probability_calibrated":False,
            "live_prediction_enabled":False,
            "horizon_sessions":HORIZON,
            "eligibility":{"bottom":"SPY <= 93% of trailing 126-session close high",
                           "top":"SPY >= 107% of trailing 126-session close low",
                           "asof_only":True,"eligibility_feature_excluded_from_predictors":True},
            "common_complete_case_features":list(KEYS),
            "families":{k:list(v) for k,v in GROUPS.items()},
            "comparison":"paired walk-forward same eligible train/test rows per variant",
            "training_cutoff":"first_test_index - 20-session_purge - 10-session_outcome_maturity",
            "limitations":["original provider vintages are not PIT verified",
                "eligibility is part of the label definition; predictions only conditional on eligibility",
                "calendar-year block bootstrap is not independent market-cycle bootstrap",
                "stress eligibility clusters are not independently adjudicated market crashes",
                "no calibration permission or investment thresholds",
                "HYG/LQD is a relative price proxy, not HY OAS",
                "small numbers of eligible events can prevent fitting",
                "non-overlap in same fold does not guarantee independence between crises"],
            "results":report}
    output["research_evidence_gate"]=conservative_research_gate(output)
    return output
