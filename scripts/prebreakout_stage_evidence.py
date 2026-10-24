#!/usr/bin/env python3
"""Descriptive, stage-stratified evidence for point-in-time prebreakout evaluations.

No hit-rate estimate is released before a predeclared minimum sample.
Intervals quantify sampling uncertainty, not forecasting accuracy.
"""
from __future__ import annotations
import math
from statistics import mean, median
from prebreakout_forward_evaluation import HORIZONS

STAGES=("compressão","pré-breakout","confirmado")
MIN_SAMPLE=30

def wilson(successes:int, n:int, z:float=1.96):
    if n<1 or not 0<=successes<=n:raise ValueError("invalid binomial evidence")
    p=successes/n
    d=1+z*z/n
    center=(p+z*z/(2*n))/d
    half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return [max(0,center-half),min(1,center+half)]

def report(evaluations:list[dict],horizons=HORIZONS,min_sample:int=MIN_SAMPLE)->dict:
    if min_sample<1:raise ValueError("min_sample must be positive")
    output={"schema":"vestra_prebreakout_stage_evidence_v1",
        "method":"observed_point_in_time_adjusted_close",
        "minimum_sample":min_sample,"stages":{}}
    for stage in STAGES:
        cohort=[e for e in evaluations if e.get("stage")==stage]
        periods={}
        for horizon in horizons:
            valid=[];missing=0
            for observation in cohort:
                result=observation.get("results",{}).get(horizon)
                if not isinstance(result,dict) or any(
                    not isinstance(result.get(key),(int,float)) or not math.isfinite(result[key])
                    for key in ("return","excess_return","max_adverse_excursion")
                ):
                    missing+=1
                    continue
                valid.append(result)
            n=len(valid)
            record={"n":n,"n_missing":missing,"n_observations":len(cohort),
                "coverage":n/len(cohort) if cohort else None,
                "sufficient_sample":n>=min_sample}
            if record["sufficient_sample"]:
                hits=sum(r["return"]>0 for r in valid)
                excess_hits=sum(r["excess_return"]>0 for r in valid)
                record.update({"hit_rate":hits/n,"hit_rate_wilson_95":wilson(hits,n),
                    "benchmark_outperformance_rate":excess_hits/n,
                    "benchmark_outperformance_wilson_95":wilson(excess_hits,n),
                    "mean_return":mean(r["return"] for r in valid),
                    "median_return":median(r["return"] for r in valid),
                    "mean_excess_return":mean(r["excess_return"] for r in valid),
                    "median_excess_return":median(r["excess_return"] for r in valid),
                    "mean_max_adverse_excursion":mean(r["max_adverse_excursion"] for r in valid)})
            else:
                record["reason"]="insufficient_forward_sample"
            periods[str(horizon)]=record
        output["stages"][stage]=periods
    return output
