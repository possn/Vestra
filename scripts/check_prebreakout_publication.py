#!/usr/bin/env python3
"""Fail closed before publishing a scanner snapshot with inconsistent evidence."""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def assess_gate_funnel(feed:dict, *, require:bool=False)->dict:
    """First-failing structural gate accounting, never a forward probability.

    Provider failures and rows without usable OHLCV are separate from
    observed per-row gate rejections; a count alone cannot imply a setup rate.
    """
    funnel=feed.get("gate_funnel")
    if funnel is None:
        return ({"status":"invalid","reason":"missing_modern_gate_funnel"}
                if require else {"status":"legacy_without_gate_funnel"})
    shadow=feed.get("quality_filter_shadow")
    if not isinstance(funnel,dict) or not isinstance(shadow,dict):
        return {"status":"invalid","reason":"missing_gate_funnel_context"}
    counts=funnel.get("first_rejection_counts")
    observed=funnel.get("observed_rows")
    passed=funnel.get("structurally_passed")
    currency_rejected=funnel.get("currency_or_usd_liquidity_rejections_after_structural_pass")
    compared=shadow.get("compared")
    strict=shadow.get("strict_eligible")
    attempted=feed.get("attempted")
    actual=feed.get("new_signals")
    numbers=[observed,passed,currency_rejected,compared,strict,attempted,actual]
    if (not isinstance(counts,dict) or
        any(type(x) is not int or x<0 for x in numbers) or
        any(not isinstance(k,str) or not k or type(v) is not int or v<0
            for k,v in counts.items())):
        return {"status":"invalid","reason":"invalid_gate_funnel_counts"}
    if (funnel.get("scope")!="current_observed_slot_only" or
        funnel.get("method")!="first_failing_gate_in_order_not_independent_gate_intersections" or
        funnel.get("missing_downloads_not_negative_evidence") is not True or
        funnel.get("probability_or_forward_performance","not_specified") is not None):
        return {"status":"invalid","reason":"gate_funnel_provenance_or_probability"}
    if (sum(counts.values())!=observed or observed!=compared or
        passed!=counts.get("passed_structural_gates",0) or
        passed!=strict or observed>attempted or currency_rejected>passed or
        actual>passed-currency_rejected):
        return {"status":"invalid","reason":"inconsistent_gate_funnel_accounting"}
    return {"status":"valid","observed_rows":observed,
            "not_observed_rows":attempted-observed,
            "structurally_passed":passed,
            "currency_or_usd_liquidity_rejections":currency_rejected,
            "model_evidence":"first_failed_gate_only_not_independent_probabilities"}


def assess_freshness(feed:dict, now:datetime, max_age_hours:float=8)->dict:
    """Read-only operational check; never infer full coverage from slot capacity."""
    if not isinstance(feed,dict) or feed.get("schema")!="vestra_prebreakout_v1":
        return {"status":"invalid","reason":"invalid_schema"}
    try:
        generated=datetime.fromisoformat(str(feed["generated_at"]).replace("Z","+00:00"))
        if generated.tzinfo is None or now.tzinfo is None:
            return {"status":"invalid","reason":"naive_timestamp"}
        if generated.astimezone(timezone.utc).date().isoformat()>="2026-11-08":
            gate=assess_gate_funnel(feed,require=True)
            if gate["status"]!="valid":
                return gate
        age=(now-generated).total_seconds()/3600
        if not 0<=age<=max_age_hours:
            return {"status":"stale","age_hours":round(age,2)}
        slot=feed["scan_slot_telemetry"]
        audit=feed["scan_quality_audit"]
        coverage=feed["coverage_audit_24h"]
        capacity=feed["daily_capacity_ceiling"]
        expected=min(1200,feed["eligible_universe"])
        if (not isinstance(slot,dict) or not isinstance(audit,dict) or
            not isinstance(capacity,dict) or
            capacity.get("max_distinct_daily")!=expected or
            slot.get("rows_attempted")!=feed["attempted"] or
            audit.get("observed_24h_coverage_pct")!=coverage["coverage_pct"]):
            return {"status":"invalid","reason":"inconsistent_new_telemetry"}
        pct=coverage.get("coverage_pct")
        if (pct is not None and (type(pct) not in (int,float) or not 0<=pct<=100)):
            return {"status":"invalid","reason":"impossible_coverage_pct"}
        # In modern publications, the numerator is the intersection with the
        # current eligible universe; older observations remain audit evidence.
        current=coverage.get("current_eligible_verified_distinct")
        if current is not None:
            observed=coverage.get("distinct_ohlcv_tickers")
            outside=coverage.get("outside_current_universe_distinct")
            eligible=feed["eligible_universe"]
            if (any(type(v) is not int for v in (current,observed,outside,eligible)) or
                not 0<=current<=eligible or outside<0 or observed!=current+outside or
                (eligible and abs(pct-round(100*current/eligible,2))>0.01) or
                audit.get("full_universe_verified")!=(eligible>0 and current==eligible)):
                return {"status":"invalid","reason":"inconsistent_current_universe_coverage"}
    except (KeyError,TypeError,ValueError,AttributeError):
        return {"status":"invalid","reason":"missing_new_telemetry"}
    return {"status":"healthy","age_hours":round(age,2),
            "observed_24h_coverage_pct":coverage["coverage_pct"]}


def verify(root:Path=ROOT):
    data=root/"data"
    feed=json.loads((data/"prebreakout-signals.json").read_text(encoding="utf-8"))
    index=json.loads((data/"prebreakout-observations.json").read_text(encoding="utf-8"))
    stamp=datetime.fromisoformat(str(feed["generated_at"]).replace("Z","+00:00"))
    if stamp.tzinfo is None:raise ValueError("publisher must use timezone-aware timestamp")
    utc=stamp.astimezone(timezone.utc)
    slot=feed.get("scan_slot_utc")
    if type(slot) is not int or slot!=utc.hour//6:raise ValueError("incorrect scanner slot")
    if feed.get("schema")!="vestra_prebreakout_v1" or not isinstance(feed.get("signals"),list):
        raise ValueError("invalid current publisher")
    file=data/"prebreakout-history"/str(utc.year)/"slots"/f"{utc.date().isoformat()}-slot{slot}.json"
    archived=json.loads(file.read_text(encoding="utf-8"))
    if archived!=feed:raise ValueError("published slot differs from feed")
    if utc.date().isoformat()>="2026-11-08":
        # Publication must enforce the complete telemetry and current-universe
        # coverage contract, not only the structural funnel. Validate as of the
        # producer timestamp so GitHub scheduling delays do not reclassify
        # otherwise valid archived evidence as invalid due to wall-clock age.
        checked=assess_freshness(feed,utc)
        if checked["status"]!="healthy":
            raise ValueError("invalid published scanner evidence: "+str(checked.get("reason") or checked["status"]))
    if index.get("schema")!="vestra_prebreakout_observations_v1" or index.get("historical_only") is not True:
        raise ValueError("observations must remain historical only")
    if not isinstance(index.get("observations"),list) or index.get("slots_considered",0)<1:
        raise ValueError("missing archived observation evidence")
    observations={row.get("ticker"):row for row in index["observations"]}
    for row in feed["signals"]:
        candidate=observations.get(row["ticker"])
        if candidate is None:raise ValueError("latest observed ticker missing from historical index")
        verified=row.get("scanner_verified_at")
        if verified is not None:
            observed=datetime.fromisoformat(str(verified).replace("Z","+00:00"))
            if observed.tzinfo is None or observed.astimezone(timezone.utc)>utc:
                raise ValueError("invalid signal verification time")
            expected=observed.astimezone(timezone.utc).isoformat()
        else:
            expected=utc.isoformat()  # Legacy archives lacked per-row provenance.
        if candidate.get("observed_at")!=expected:raise ValueError("observation timestamp mismatch")
        if candidate.get("stage")!=row["stage"] or candidate.get("signal_date")!=row["date"]:
            raise ValueError("latest observation stage/date mismatch")
        if candidate.get("current") is not False:raise ValueError("history promoted to current")
    return {"verified_slot":slot,"observations":len(index["observations"]),"new_signals":len(feed["signals"])}

if __name__=="__main__":
    print(json.dumps(verify()))
