#!/usr/bin/env python3
"""Paired, as-observed pre-breakout gate audit: research only, no live ranking.

Every comparison uses the very same observed ticker rows from one canonical
scanner publication. A missing research field is never counted as a failure
or as a passing signal. The output is descriptive, not a backtest.
"""
from __future__ import annotations
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data/prebreakout-signals.json"
OUTPUT = ROOT / "data/prebreakout-paired-gate-audit.json"

def summarize(feed: dict) -> dict:
    if feed.get("schema") != "vestra_prebreakout_v1":
        raise ValueError("invalid canonical prebreakout feed")
    try:
        stamp = datetime.fromisoformat(feed["generated_at"].replace("Z", "+00:00"))
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise ValueError("invalid feed timestamp") from exc
    if stamp.tzinfo is None:
        raise ValueError("naive feed timestamp")
    block = feed.get("research_observations")
    if not isinstance(block, dict) or not isinstance(block.get("rows"), list):
        raise ValueError("missing as-observed research rows")
    rows = block["rows"]
    if len(rows) != feed.get("attempted") or type(feed.get("attempted")) is not int:
        raise ValueError("research denominator differs from attempted scan")
    observed = {}
    counts = Counter()
    ma_checks = Counter()
    samples = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("malformed research row")
        ticker = row.get("ticker")
        if not isinstance(ticker, str) or not ticker.strip() or ticker in observed:
            raise ValueError("missing or duplicate ticker identity")
        observed[ticker] = row
        if row.get("evaluable") is not True:
            counts["not_evaluable"] += 1
            continue
        counts["evaluable"] += 1
        geom = row.get("geometry_shadow")
        lineage = row.get("research_prebreakout_lineage")
        first = row.get("first_rejection")
        if not isinstance(geom, dict) or not isinstance(lineage, dict) or not isinstance(first, str):
            counts["missing_matched_evidence"] += 1
            continue
        base = geom.get("base_width_pass")
        vcp = geom.get("contractions_pass")
        intact = lineage.get("unbroken_prebreakout_position")
        if any(type(v) is not bool for v in (base, vcp, intact)):
            counts["missing_matched_evidence"] += 1
            continue
        counts["paired_evaluable"] += 1
        counts["base_width_pass"] += int(base)
        counts["sequential_contractions_pass"] += int(vcp)
        counts["both_geometry_pass"] += int(base and vcp)
        counts["both_geometry_below_unbroken_pivot"] += int(base and vcp and intact)
        rejected_ma = first == "moving_average_structure"
        counts["ma_first_rejection"] += int(rejected_ma)
        counts["geometry_both_rejected_ma"] += int(base and vcp and rejected_ma)
        counts["geometry_both_unbroken_rejected_ma"] += int(base and vcp and intact and rejected_ma)
        counts["strict_structural_pass"] += int(first == "passed_structural_gates")
        if rejected_ma:
            for item in row.get("ma_failed_checks", []):
                if isinstance(item, str) and item:
                    ma_checks[item] += 1
        if base and vcp and intact and rejected_ma:
            technical = row.get("technical_evidence_shadow")
            samples.append({
                "ticker": ticker,
                "first_rejection": first,
                "ma_failed_checks": sorted(row.get("ma_failed_checks") or []),
                "close_position20": technical.get("close_position20") if isinstance(technical, dict) else None,
                "relative_strength_observed": (
                    technical.get("relative_strength_to_index") is not None
                    if isinstance(technical, dict) else False),
                "research_only": True,
            })
    funnel = feed.get("gate_funnel")
    if not isinstance(funnel, dict) or funnel.get("observed_rows") != len(rows):
        raise ValueError("research rows do not reconcile with canonical gate funnel")
    if counts["ma_first_rejection"] > funnel.get("first_rejection_counts", {}).get("moving_average_structure", -1):
        raise ValueError("paired MA rejected count exceeds canonical funnel")
    return {
        "schema": "vestra_prebreakout_paired_gate_audit_v1",
        "observed_at": feed["generated_at"],
        "scope": "same_slot_same_ticker_as_observed_not_out_of_sample",
        "eligible_universe": feed.get("eligible_universe"),
        "attempted": len(rows),
        "counts": dict(sorted(counts.items())),
        "overlapping_ma_failed_checks": dict(sorted(ma_checks.items())),
        "research_only_not_signal": True,
        "forecast_performance_validated": False,
        "calibrated_probability": None,
        "sample_not_recommendations": sorted(samples, key=lambda x: x["ticker"]),
        "interpretation": "Structural comparison only; no forward returns, no changed gates or rank.",
    }

def main() -> None:
    report = summarize(json.loads(INPUT.read_text(encoding="utf-8")))
    OUTPUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"observed_at": report["observed_at"], "counts": report["counts"]}))

if __name__ == "__main__":
    main()
