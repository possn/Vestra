#!/usr/bin/env python3
"""Research-only descriptive discrimination of pre-breakout features.

Consumes retrospective_feature_outcome_audit records; never fits a model or
interprets observations as independent trials. No production ranking changes.
"""
from __future__ import annotations
import math
from statistics import median

FEATURES=("atr14_pct","recent5_vs_prior15_volume_ratio",
          "stock_return_20_sessions","relative_return_20_vs_spy")
LABELS=("confirmed","not_confirmed")

def compare_features(records:list[dict], min_per_group:int=30)->dict:
    if type(min_per_group) is not int or min_per_group<1:
        raise ValueError("invalid minimum cohort evidence")
    result={"method":"univariate_descriptive_medians_no_independence_claim",
            "predictive_validity_established":False,"probabilities_calibrated":False,
            "out_of_sample_tested":False,"minimum_per_group":min_per_group,
            "by_horizon":{}}
    for h in (5,10,20):
        horizon=[r for r in records if isinstance(r,dict) and r.get("horizon_sessions")==h]
        usable=[r for r in horizon if r.get("outcome") in LABELS]
        cell={"cohorts":len(horizon),"matured_labeled":len(usable),
              "excluded_pending_or_unverified":len(horizon)-len(usable),"features":{}}
        for key in FEATURES:
            groups={label:[] for label in LABELS}
            for r in usable:
                if r.get("features_point_in_time_verified") is True:
                    # This audit is deliberately conservative even if an input claims verified.
                    pass
                val=r.get("features",{}).get(key) if isinstance(r.get("features"),dict) else None
                if type(val) not in (int,float) or not math.isfinite(val):continue
                groups[r["outcome"]].append(val)
            a,b=groups["confirmed"],groups["not_confirmed"]
            enough=len(a)>=min_per_group and len(b)>=min_per_group
            cell["features"][key]={"confirmed_n":len(a),"not_confirmed_n":len(b),
                "confirmed_median":round(median(a),6) if a else None,
                "not_confirmed_median":round(median(b),6) if b else None,
                "median_difference":round(median(a)-median(b),6) if a and b else None,
                "minimum_descriptive_evidence_met":enough,
                "significance_tested":False,"independence_verified":False,
                "selection_effect_validated":False}
        result["by_horizon"][str(h)]=cell
    return result
