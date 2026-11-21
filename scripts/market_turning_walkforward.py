#!/usr/bin/env python3
"""Purged, chronological research-only market-turning validation.

Inputs are same-source historical price series retrieved today; they are NOT
verified original point-in-time vintages. Never publish outputs as calibrated
probabilities or use as live Vestra votes.
"""
from __future__ import annotations
import json
import math
from market_turning_feature_lab import series, feature_row, future_reversal_labels

TICKERS = ("SPY", "^VIX", "^VVIX", "^COR1M", "^VIX3M", "HYG", "LQD")
FEATURES = ("drawdown_126_pct", "vix_percentile_126",
            "rsi_daily_5", "rsi_weekly_14", "mfi_daily_14")
HORIZONS = (5, 10, 20)
PURGE = 20
FOLD = 252
MIN_TRAIN = 1008
EPS = 1e-9

def sigmoid(value):
    value = max(-35., min(35., value))
    return 1. / (1. + math.exp(-value))

def fit(train, keys):
    """Train-only standardization, deterministic L2 logistic SGD."""
    x = [[v["features"][key] for key in keys] for v in train]
    y = [int(v["label"]) for v in train]
    if min(sum(y), len(y)-sum(y)) < 15:
        return None
    means = [sum(row[j] for row in x)/len(x) for j in range(len(keys))]
    stds = [max((sum((row[j]-means[j])**2 for row in x)/len(x))**.5, 1e-6)
            for j in range(len(keys))]
    z = [[max(-6., min(6., (row[j]-means[j])/stds[j]))
          for j in range(len(keys))] for row in x]
    weights = [0.] * len(keys)
    bias = math.log(max(EPS, sum(y)/len(y)) / max(EPS, 1.-sum(y)/len(y)))
    # Batch gradient descent avoids dependence on row-order or a random seed.
    for step in range(350):
        gb = 0.
        gw = [0.] * len(keys)
        for row, target in zip(z, y):
            err = sigmoid(bias + sum(a*b for a,b in zip(row,weights))) - target
            gb += err
            for j,val in enumerate(row):
                gw[j] += err*val
        lr = .12 / (1. + step/180.)
        bias -= lr*gb/len(y)
        for j in range(len(keys)):
            weights[j] -= lr*(gw[j]/len(y) + .06*weights[j])
    return means, stds, weights, bias

def predict(model, features, keys):
    means, stds, weights, bias = model
    z = [max(-6., min(6., (features[k]-means[j])/stds[j]))
         for j,k in enumerate(keys)]
    return sigmoid(bias + sum(w*v for w,v in zip(weights,z)))

def metrics(pairs):
    if not pairs:
        return None
    n = len(pairs)
    brier = sum((p-y)**2 for p,y in pairs)/n
    logloss = -sum(y*math.log(max(EPS,p))+(1-y)*math.log(max(EPS,1-p))
                   for p,y in pairs)/n
    positives = sum(y for _,y in pairs)
    bins = []
    for low,high in ((0,.2),(.2,.4),(.4,.6),(.6,.8),(.8,1.000001)):
        subset = [(p,y) for p,y in pairs if low <= p < high]
        if subset:
            bins.append({"range": [low, min(high,1.)], "n": len(subset),
                         "mean_forecast": round(sum(p for p,_ in subset)/len(subset),4),
                         "event_frequency": round(sum(y for _,y in subset)/len(subset),4)})
    return {"n_nonoverlapping_test_anchors": n, "events": positives,
            "event_prevalence": round(positives/n,5),
            "brier": round(brier,6), "log_loss": round(logloss,6),
            "calibration_bins": bins}

def evaluate(raw):
    histories = {key: series(raw,key) for key in TICKERS}
    spy = histories["SPY"]
    if len(spy) < MIN_TRAIN+PURGE+FOLD+125:
        return {"evaluated": False, "reason": "insufficient_history"}
    rows = []
    for index in range(125,len(spy)):
        day = spy[index]["date"]
        features = feature_row(histories,day)
        if features is not None:
            rows.append((index,day,features))
    results = {}
    for horizon in HORIZONS:
        directions = {}
        for side in ("bottom","top"):
            samples=[]
            for index,day,features in rows:
                label = future_reversal_labels(spy,index,forward=horizon,
                    nearby=min(5,horizon-1))[side]
                if label is None:
                    continue
                samples.append({"index":index,"date":day,"features":features,
                                "label":int(label)})
            forecasts, baselines, fold_meta = [], [], []
            for start in range(MIN_TRAIN,len(samples),FOLD):
                # Last train label's full forward horizon must end before first test.
                training = [v for v in samples[:max(0,start-PURGE)]
                            if all(v["features"][k] is not None for k in FEATURES)]
                testing = [v for v in samples[start:start+FOLD]
                           if all(v["features"][k] is not None for k in FEATURES)]
                if not training or not testing:
                    continue
                model=fit(training,FEATURES)
                if model is None:
                    continue
                prevalence=sum(v["label"] for v in training)/len(training)
                # One decision every horizon sessions: prevent overlapping
                # forward outcomes from masquerading as independent episodes.
                sampled=[]
                last_anchor=-100000
                for item in testing:
                    if item["index"]-last_anchor < horizon:
                        continue
                    sampled.append(item)
                    last_anchor=item["index"]
                for item in sampled:
                    forecasts.append((predict(model,item["features"],FEATURES),item["label"]))
                    baselines.append((prevalence,item["label"]))
                fold_meta.append({"first":sampled[0]["date"] if sampled else None,
                                  "last":sampled[-1]["date"] if sampled else None,
                                  "train_n":len(training),"test_independent_anchors":len(sampled)})
            model_metrics,base_metrics=metrics(forecasts),metrics(baselines)
            directions[side]={"model":model_metrics,"train_prevalence_baseline":base_metrics,
                "brier_skill_vs_baseline":round(1-model_metrics["brier"]/base_metrics["brier"],5)
                    if model_metrics and base_metrics and base_metrics["brier"] else None,
                "folds":fold_meta,
                "validated_for_live_probability":False}
        results[str(horizon)]=directions
    return {"schema":"vestra_market_turning_walkforward_research_v1",
            "research_only":True,"probability_calibrated":False,
            "original_point_in_time_vintages_verified":False,
            "live_score_changed":False,"features":list(FEATURES),
            "horizons_sessions":list(HORIZONS),
            "purge_sessions":PURGE,"fold_sessions":FOLD,
            "min_training_sessions":MIN_TRAIN,
            "independence":"test anchors >= horizon sessions; not independent market cycles",
            "baseline":"expanding training prevalence, not full-sample prevalence",
            "limitations":["retrospectively adjusted historical series are not original PIT vintages",
              "no event-cluster confidence intervals","no out-of-sample calibration approval",
              "no family ablations or regimes yet","threshold labels are research definitions"],
            "results":results}

def main():
    import argparse
    from pathlib import Path
    parser=argparse.ArgumentParser()
    parser.add_argument("--input",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    report=evaluate(json.loads(args.input.read_text(encoding="utf-8")))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+"\n",
                           encoding="utf-8")

if __name__=="__main__":
    main()
