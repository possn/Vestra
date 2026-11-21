#!/usr/bin/env python3
"""Stress-conditioned, paired chronological ablations (research only).

Outcome labels remain fixed, but only sessions already eligible by prior stress
enter evaluation. The preceding drawdown/run-up is *not* a predictor: it is a
necessary condition of the label and previously inflated unconditional skill.
All variants use identical as-of rows and test anchors; no cherry-picked sample
per factor. Reports are never calibrated live probabilities.
"""
from __future__ import annotations
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
        by_model={name:[] for name in variants()}
        baseline=[]
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
        }
    return {"schema":"vestra_stress_conditioned_ablation_research_v1",
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
                "no market-cycle cluster confidence intervals",
                "no calibration permission or investment thresholds",
                "HYG/LQD is a relative price proxy, not HY OAS",
                "small numbers of eligible events can prevent fitting",
                "non-overlap in same fold does not guarantee independence between crises"],
            "results":report}
