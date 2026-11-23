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
    alternative = Counter()
    alternative_missing = Counter()
    independent_ma_geometry = Counter()
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
        # First-failing-gate counts cannot quantify the independent effect of
        # a moving-average gate. A prospective paired 2x2 captures the exact
        # same ticker/session without changing public eligibility.
        ma = row.get("ma_structure_shadow")
        if (isinstance(ma, dict) and ma.get("status") == "measured"
                and ma.get("research_only_no_eligibility_or_score_effect") is True
                and all(type(ma.get(k)) is bool for k in
                        ("all_pass", "price_order_pass", "three_slopes_rising"))
                and ma["all_pass"] == (ma["price_order_pass"] and ma["three_slopes_rising"])
                and not (rejected_ma and ma["all_pass"])
                and not (first == "passed_structural_gates" and not ma["all_pass"])):
            geom_pass = base and vcp and intact
            independent_ma_geometry["paired_rows"] += 1
            key = ("geometry_pass_" if geom_pass else "geometry_fail_") + (
                "ma_pass" if ma["all_pass"] else "ma_fail")
            independent_ma_geometry[key] += 1
        else:
            independent_ma_geometry["missing_or_conflicting_ma_capture"] += 1
        # Independent swing geometry and shifted-window stability are measured
        # on this exact ticker and session, never on a different population.
        swing = row.get("swing_geometry_shadow")
        phase = row.get("geometry_phase_shadow")
        if (isinstance(swing, dict) and swing.get("status") == "measured"
                and type(swing.get("all_geometry_pass")) is bool):
            swing_pass = swing["all_geometry_pass"]
            alternative["swing_comparable"] += 1
            alternative["swing_pass"] += int(swing_pass)
            alternative["fixed_pass_on_swing_sample"] += int(base and vcp and intact)
            alternative["both_fixed_and_swing_pass"] += int(base and vcp and intact and swing_pass)
            alternative["swing_only_pass"] += int(swing_pass and not (base and vcp and intact))
        else:
            alternative_missing["swing"] += 1
        if (isinstance(phase, dict)
                and phase.get("phase_offsets_sessions") == list(range(11))
                and type(phase.get("both_pass_count")) is int
                and 0 <= phase["both_pass_count"] <= 11
                and type(phase.get("canonical_both_pass")) is bool
                and phase["canonical_both_pass"] == (base and vcp)):
            robust = phase["both_pass_count"] >= 2
            alternative["phase_comparable"] += 1
            alternative["phase_any_pass"] += int(phase["both_pass_count"] > 0)
            alternative["phase_two_or_more_pass"] += int(robust)
            alternative["fixed_pass_on_phase_sample"] += int(base and vcp)
            alternative["fixed_pass_phase_robust"] += int(base and vcp and robust)
            alternative["alternate_phase_only"] += int(not (base and vcp) and phase["both_pass_count"] > 0)
        else:
            alternative_missing["phase"] += 1

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
        "independent_ma_geometry_matrix": {
            "counts": dict(sorted(independent_ma_geometry.items())),
            "scope": "same_ticker_same_slot_completed_bars_only",
            "missing_captures_not_assumed_to_fail": True,
            "descriptive_not_an_ablation_or_forward_validation": True,
            "no_signal_or_ranking_effect": True,
        },
        "alternative_geometry_comparison": {
            "method": "same_ticker_same_slot_complete_case_only",
            "counts": dict(sorted(alternative.items())),
            "missing_or_unverifiable": dict(sorted(alternative_missing.items())),
            "swing_geometry_is_independent_not_a_live_signal": True,
            "phase_stability_requires_2_of_11_lags": True,
            "no_outcome_or_precision_claim": True,
        },
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
