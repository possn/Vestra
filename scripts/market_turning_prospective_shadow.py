#!/usr/bin/env python3
"""Append-only research forecasts, frozen BEFORE future 10-session outcomes exist.

The model output is an experimental research quantity, NOT a calibrated
probability, live bottom/top signal or permission to trade. Inputs use
completed provider bars retrieved at issue time, and provenance is explicit.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from market_turning_feature_lab import series, feature_row, future_reversal_labels
from market_turning_walkforward import fit, predict
from market_turning_conditional_ablations import KEYS

ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/"data/market-turning-prospective"
OUTCOME_ARCHIVE=ROOT/"data/market-turning-prospective-outcome-ledger"
HORIZON=10
EMBARGO=20
MIN_ELIGIBLE_TRAIN=150
SYMBOLS=("SPY","^VIX","^VIX3M","HYG","LQD")
MODEL_VERSION="l2_stress_conditional_10s_v1_frozen_20261121"

def eligible(past, side):
    if len(past)<126:
        return False
    close=past[-1]["close"]
    previous=[r["close"] for r in past[-126:]]
    return (close<=max(previous)*.93 if side=="bottom"
            else close>=min(previous)*1.07)

def freeze(raw, generated_at):
    if generated_at.tzinfo is None:
        raise ValueError("UTC-aware generated_at required")
    histories={key:series(raw,key) for key in SYMBOLS}
    spy=histories["SPY"]
    if len(spy)<126+HORIZON+EMBARGO+1008:
        return {"available":False,"reason":"insufficient_historical_spy"}
    asof=spy[-1]["date"]
    if asof>=generated_at.date().isoformat():
        raise ValueError("incomplete_or_future_daily_bar")
    feats=feature_row(histories,asof)
    if feats is None:
        return {"available":False,"reason":"feature_extraction_failed"}
    current={key:feats[key] for key in KEYS}
    nonmissing=all(value is not None for value in current.values())
    digest=hashlib.sha256(json.dumps(raw,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    output={"schema":"vestra_turning_prospective_shadow_v1",
        "model_version":MODEL_VERSION,
        "observation_date":asof,"created_at":generated_at.isoformat(),
        "research_only":True,"calibrated_probability":False,
        "live_score_changed":False,"eligible_horizon_sessions":HORIZON,
        "source":{"provider":"yahoo_finance","retrieved_now_adjusted_history":True,
          "original_daily_vintage_independently_verified":False,
          "source_history_sha256":digest,
          "spy_observed_close":spy[-1]["close"]},
        "features":current,
        "feature_coverage":{"observed":sum(v is not None for v in current.values()),
            "total":len(KEYS),"complete":nonmissing},
        "training":{"embargo_sessions":EMBARGO,
            "forward_outcome_maturity_sessions":HORIZON,
            "max_training_anchor_index":len(spy)-1-HORIZON-EMBARGO},
        "sides":{}}
    for side in ("bottom","top"):
        active=eligible(spy,side)
        record={"eligible_contemporaneously":active,
                "eligible_condition":"past_126_spy_drawdown_ge_7pct" if side=="bottom"
                else "past_126_spy_rally_ge_7pct",
                "model_output_uncalibrated_not_for_live_display":None,
                "conditional_train_prevalence":None,
                "train_eligible_rows":0,
                "reason":"market_not_eligible" if not active else "training_or_features_unavailable"}
        if active and nonmissing:
            history=[]
            # Full forward maturity plus embargo; no outcome from the current
            # period may affect fitting or standardization.
            for i in range(125,len(spy)-HORIZON-EMBARGO):
                if not eligible(spy[:i+1],side):
                    continue
                day=spy[i]["date"]
                row=feature_row(histories,day)
                if row is None or any(row[key] is None for key in KEYS):
                    continue
                label=future_reversal_labels(spy,i,forward=HORIZON,nearby=5)[side]
                if label is not None:
                    history.append({"date":day,"features":row,"label":int(label)})
            record["train_eligible_rows"]=len(history)
            if len(history)>=MIN_ELIGIBLE_TRAIN:
                model=fit(history,KEYS)
                if model is not None:
                    record["model_output_uncalibrated_not_for_live_display"]=round(predict(model,current,KEYS),6)
                    record["conditional_train_prevalence"]=round(
                        sum(row["label"] for row in history)/len(history),6)
                    record["reason"]="research_forecast_frozen_no_future_outcome"
        output["sides"][side]=record
    return output

def matured_shadow_assessment(archives,spy):
    """Grade only previously frozen forecasts whose forward bars have matured."""
    by_date={row["date"]:i for i,row in enumerate(spy)}
    results=[]
    for path in sorted(archives.glob("*.json")):
        record=json.loads(path.read_text(encoding="utf-8"))
        if record.get("schema")!="vestra_turning_prospective_shadow_v1":continue
        asof=record["observation_date"]
        index=by_date.get(asof)
        if index is None or index+HORIZON>=len(spy):
            continue
        sides={}
        for side in ("bottom","top"):
            record_side=record.get("sides",{}).get(side,{})
            prediction=record_side.get("model_output_uncalibrated_not_for_live_display")
            baseline=record_side.get("conditional_train_prevalence")
            if prediction is None or baseline is None:
                continue
            truth=future_reversal_labels(spy,index,forward=HORIZON,nearby=5)[side]
            if truth is None:continue
            y=int(truth)
            sides[side]={"observed_event_label":y,
                         "frozen_model_squared_error":round((prediction-y)**2,6),
                         "frozen_baseline_squared_error":round((baseline-y)**2,6)}
        if sides:
            results.append({"observation_date":asof,"matured_asof":spy[index+HORIZON]["date"],
                            "sides":sides})
    return {"schema":"vestra_turning_prospective_outcomes_v1",
            "research_only":True,"calibrated_probability":False,
            "original_outcome_vintages_verified":False,
            "total_matured_records":len(results),
            "records":results}

def freeze_matured_outcomes(archives,spy,outcome_archive,generated_at):
    """Create each matured outcome once; later adjusted-history changes cannot rewrite it.

    Newly matured labels use the provider history retrieved at assessment time.
    The source is not original vintage PIT and the evaluation remains research.
    Subsequent runs construct the public summary from frozen outcome records,
    not a fresh relabel of every historical forecast.
    """
    if generated_at.tzinfo is None:
        raise ValueError("UTC-aware generated_at required")
    possible=matured_shadow_assessment(archives,spy)["records"]
    if possible:
        outcome_archive.mkdir(parents=True,exist_ok=True)
    price_digest=hashlib.sha256(json.dumps(
        spy,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    for item in possible:
        day=item["observation_date"]
        target=outcome_archive/(day+".json")
        if target.exists():
            # Do not alter an outcome once frozen, even if Yahoo revises its bars.
            continue
        forecast_file=archives/(day+".json")
        forecast_bytes=forecast_file.read_bytes()
        frozen={
            "schema":"vestra_turning_frozen_outcome_v1",
            **item,
            "frozen_at":generated_at.isoformat(),
            "frozen_forecast_sha256":hashlib.sha256(forecast_bytes).hexdigest(),
            "outcome_provider":"yahoo_finance_adjusted_history",
            "outcome_retrieval_sha256":price_digest,
            "original_outcome_vintage_verified":False,
            "research_only":True,
            "calibrated_probability":False,
        }
        # Exclusive creation protects against accidental same-run overwrite.
        try:
            with target.open("x",encoding="utf-8") as out:
                out.write(json.dumps(frozen,indent=2,ensure_ascii=False,allow_nan=False)+"\\n")
        except FileExistsError:
            pass

    records=[]
    for path in sorted(outcome_archive.glob("*.json")):
        row=json.loads(path.read_text(encoding="utf-8"))
        if row.get("schema")!="vestra_turning_frozen_outcome_v1":
            raise ValueError("unexpected_or_unverifiable_frozen_outcome_record")
        if path.stem!=row.get("observation_date"):
            raise ValueError("frozen_outcome_filename_mismatch")
        records.append(row)
    return {
        "schema":"vestra_turning_prospective_outcomes_v2",
        "research_only":True,
        "calibrated_probability":False,
        "original_outcome_vintages_verified":False,
        "outcomes_append_only":True,
        "total_matured_records":len(records),
        "records":records,
    }

def main():
    from refresh_market_turning_feature_lab import normalize_yahoo
    import yfinance as yf
    now=datetime.now(timezone.utc)
    raw={}
    for symbol in SYMBOLS:
        data=yf.download(symbol,start="2004-01-01",end=now.date().isoformat(),
                         auto_adjust=True,threads=False,multi_level_index=False,progress=False)
        raw[symbol]=normalize_yahoo(data,now.date())
    result=freeze(raw,now)
    if not result.get("schema"):
        raise ValueError("insufficient independent inputs for frozen research record")
    ARCHIVE.mkdir(parents=True,exist_ok=True)
    output=ARCHIVE/(result["observation_date"]+".json")
    if output.exists():
        print("Immutable prospectively frozen snapshot exists:",output)
    else:
        output.write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+"\n",encoding="utf-8")
        print("Created research-only forecast:",output)
    assessments=freeze_matured_outcomes(ARCHIVE,series(raw,"SPY"),OUTCOME_ARCHIVE,now)
    out=ROOT/"data/market-turning-prospective-outcomes.json"
    out.write_text(json.dumps(assessments,indent=2,ensure_ascii=False,allow_nan=False)+"\n",encoding="utf-8")

if __name__=="__main__":
    main()
