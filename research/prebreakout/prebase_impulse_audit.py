#!/usr/bin/env python3
"""Research-only, point-in-time descriptive audit of pre-base impulse morphology.

The units must be distinct frozen base/pivot episodes; observations with no
verifiable point-in-time feature provenance or immature labels are excluded.
No thresholds, classifications, live ranking or probabilities are produced.
"""
from __future__ import annotations
import math
from statistics import median

FEATURES=("preBaseReturn40Pct","preBaseRange40Pct","contractionWidths20Pct")
LABELS=("confirmed","not_confirmed")

def audit(records:list[dict], min_per_group:int=30)->dict:
    if type(min_per_group) is not int or min_per_group<1:
        raise ValueError("invalid minimum cohort evidence")
    output={"method":"point_in_time_episode_descriptive_only",
            "predictive_validity_established":False,
            "out_of_sample_tested":False,
            "live_gate_approved":False,
            "minimum_per_group":min_per_group,"by_horizon":{}}
    for horizon in (5,10,20):
        subset=[r for r in records if isinstance(r,dict) and r.get("horizon_sessions")==horizon]
        used=set()
        groups={label:{key:[] for key in FEATURES} for label in LABELS}
        excluded={"unknown_outcome":0,"unverified_asof":0,"missing_features":0,"duplicate_episode":0}
        for row in subset:
            if row.get("outcome") not in LABELS or row.get("outcome_matured") is not True:
                excluded["unknown_outcome"]+=1
                continue
            if row.get("features_point_in_time_verified") is not True:
                excluded["unverified_asof"]+=1
                continue
            episode=row.get("episode_id")
            if not isinstance(episode,str) or not episode.strip():
                excluded["unverified_asof"]+=1
                continue
            if episode in used:
                excluded["duplicate_episode"]+=1
                continue
            feats=row.get("features")
            if not isinstance(feats,dict) or not feats:
                excluded["missing_features"]+=1
                continue
            used.add(episode)
            label=row["outcome"]
            for key in FEATURES:
                v=feats.get(key)
                if key=="contractionWidths20Pct":
                    if not isinstance(v,(tuple,list)) or len(v)!=3 or any(type(x) not in (int,float) or not math.isfinite(x) or x<=0 for x in v):
                        continue
                    # A geometric contraction requires strictly narrowing widths.
                    # A widening/noisy sequence must stay missing, not be
                    # misreported as an observed VCP contraction magnitude.
                    if not (v[0] > v[1] > v[2]):
                        continue
                    # Descriptive contraction magnitude; never a standalone VCP gate.
                    v=100*(1-v[2]/v[0])
                if type(v) in (int,float) and math.isfinite(v):
                    groups[label][key].append(float(v))
        features={}
        for key in FEATURES:
            a,b=groups["confirmed"][key],groups["not_confirmed"][key]
            features[key]={"confirmed_n":len(a),"not_confirmed_n":len(b),
                "confirmed_median":round(median(a),4) if a else None,
                "not_confirmed_median":round(median(b),4) if b else None,
                "median_difference":round(median(a)-median(b),4) if a and b else None,
                "minimum_descriptive_evidence_met":len(a)>=min_per_group and len(b)>=min_per_group,
                "independence_or_predictive_edge_established":False}
        output["by_horizon"][str(horizon)]={"submitted":len(subset),
            "distinct_verified_episodes":len(used),"excluded":excluded,"features":features}
    return output
