#!/usr/bin/env python3
"""Prospective, frozen four-arm MA x VCP forward comparison; research only.

The first *eligible capture after the MA-shadow schema exists* per ticker fixes
group membership. Never relabel the first capture after observing outcomes.
Missing/incomplete price evidence remains unknown, not an unsuccessful signal.
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

from prebreakout_forward_events import breakout_event

GROUPS = (
    "geometry_pass_ma_pass",
    "geometry_pass_ma_fail",
    "geometry_fail_ma_pass",
    "geometry_fail_ma_fail",
)
HORIZONS = (5, 10, 20, 60)


def asof_activity_quality(row: dict) -> str:
    """Evidence gate only: measure activity from the original frozen scan.

    Zero price range is not volatility contraction. Missing/zero volume is
    not accumulation. No source data or later prices may repair this label.
    """
    technical = row.get("technical_evidence_shadow")
    if not isinstance(technical, dict) or technical.get("status") != "measured":
        return "technical_activity_not_measured_at_capture"
    atr = technical.get("atr14_pct")
    if type(atr) not in (int, float) or not math.isfinite(atr) or atr < 0:
        return "technical_activity_not_measured_at_capture"
    if atr == 0:
        return "no_measurable_price_range_at_capture"
    volume = technical.get("volume9_to_prior40")
    if type(volume) not in (int, float) or not math.isfinite(volume):
        return "volume_activity_unverified_at_capture"
    if volume <= 0:
        return "no_positive_volume_activity_at_capture"
    return "verified_nonflat_price_and_volume_at_capture"


def asof_swing_concordance(row: dict) -> str:
    """Independent confirmed-swing geometry, frozen at capture (research only)."""
    swing = row.get("swing_geometry_shadow")
    if not isinstance(swing, dict) or swing.get("status") != "measured":
        return "swing_geometry_not_measured"
    values = ("sequential_contraction_pass", "base_width_pass",
              "below_pivot_pass", "latest_pullback_recent", "all_geometry_pass")
    if any(type(swing.get(field)) is not bool for field in values):
        return "swing_geometry_unverified"
    if swing["all_geometry_pass"] != all(swing[field] for field in values[:-1]):
        return "swing_geometry_conflicting_capture"
    return ("swing_geometry_confirmed" if swing["all_geometry_pass"]
            else "swing_geometry_not_confirmed")


def asof_canonical_quality(row: dict) -> str:
    """Do not equate independent MA x fixed-window research passes with live eligibility."""
    reason = row.get("first_rejection")
    if reason == "passed_structural_gates":
        return "canonical_structural_gates_passed"
    if isinstance(reason, str) and reason:
        return "canonical_rejected_" + reason
    return "canonical_gate_unverified"

# Committed before the first eligible next-day scanner slot. Earlier cases
# belong exclusively to the historical four-arm diagnostic (v1).
AT_RISK_COHORT_START = "2026-11-24T02:00:00+00:00"


def select(archive: Path, per_group: int = 32, *, at_risk_only: bool = False) -> dict:
    if type(per_group) is not int or not 1 <= per_group <= 100:
        raise ValueError("invalid predeclared research cohort budget")
    first = {}
    excluded = Counter()
    start_at = datetime.fromisoformat(AT_RISK_COHORT_START) if at_risk_only else None
    instrumented_slots = 0
    instrumented_evaluable_rows = 0
    latest_instrumented_capture = None
    for path in sorted(archive.glob("*/slots/*-slot*.json")):
        try:
            snapshot = json.loads(path.read_text(encoding="utf-8"))
            stamp = datetime.fromisoformat(snapshot["generated_at"].replace("Z", "+00:00"))
            if (stamp.tzinfo is None or snapshot.get("schema") != "vestra_prebreakout_v1"):
                continue
            stamp = stamp.astimezone(timezone.utc)
            if start_at is not None and stamp < start_at:
                continue
            if (type(snapshot.get("scan_slot_utc")) is not int
                or snapshot["scan_slot_utc"] != stamp.hour // 6
                or path.name != f"{stamp.date().isoformat()}-slot{stamp.hour // 6}.json"):
                continue
            block = snapshot.get("research_observations", {})
            if (block.get("point_in_time_capture_not_historical_reconstruction") is not True
                or not isinstance(block.get("rows"), list)):
                continue
        except (OSError, ValueError, KeyError, AttributeError, TypeError):
            continue
        # This provenance is checked on the *original immutable scan*, never
        # inferred from a later build or a reconstructed price series.
        slot_instrumented_rows = sum(
            isinstance(row, dict) and row.get("evaluable") is True
            and isinstance(row.get("ma_structure_shadow"), dict)
            for row in block["rows"])
        if slot_instrumented_rows:
            instrumented_slots += 1
            instrumented_evaluable_rows += slot_instrumented_rows
            latest_instrumented_capture = stamp.isoformat()
        seen_in_slot = set()
        for row in block["rows"]:
            if not isinstance(row, dict):
                excluded["invalid_row"] += 1
                continue
            ticker = row.get("ticker")
            if (not isinstance(ticker, str) or not ticker or len(ticker) > 20
                or ticker in seen_in_slot):
                excluded["invalid_or_duplicate_ticker"] += 1
                continue
            seen_in_slot.add(ticker)
            if ticker in first or row.get("evaluable") is not True:
                continue
            geometry = row.get("geometry_shadow")
            lineage = row.get("research_prebreakout_lineage")
            ma = row.get("ma_structure_shadow")
            anchor = row.get("asof_base_price_anchor")
            if not all(isinstance(x, dict) for x in (geometry, lineage, ma, anchor)):
                excluded["missing_matched_capture"] += 1
                continue
            if (ma.get("status") != "measured"
                or ma.get("research_only_no_eligibility_or_score_effect") is not True
                or any(type(ma.get(k)) is not bool for k in
                       ("all_pass", "price_order_pass", "three_slopes_rising"))
                or ma["all_pass"] != (ma["price_order_pass"] and ma["three_slopes_rising"])):
                excluded["invalid_ma_capture"] += 1
                continue
            base, vcp, unbroken = (geometry.get("base_width_pass"),
                                  geometry.get("contractions_pass"),
                                  lineage.get("unbroken_prebreakout_position"))
            if any(type(v) is not bool for v in (base, vcp, unbroken)):
                excluded["invalid_geometry_capture"] += 1
                continue
            if at_risk_only and not unbroken:
                excluded["already_broken_at_first_capture"] += 1
                continue
            if (anchor.get("schema") != "vestra_prebreakout_asof_base_anchor_v1"
                or anchor.get("window_bars") != 40
                or anchor.get("reference_bars") != 39
                or anchor.get("historical_adjustment_factor_verified") is not False
                or anchor.get("research_only_no_eligibility_or_score_effect") is not True):
                excluded["invalid_asof_anchor"] += 1
                continue
            try:
                session = str(anchor["session"])
                close, pivot = float(anchor["adjusted_close"]), float(anchor["adjusted_pivot_high"])
                if (session != row.get("last_session") or session > stamp.date().isoformat()
                    or not all(math.isfinite(x) and x > 0 for x in (close, pivot))
                    or close > pivot):
                    raise ValueError("invalid anchor identity")
            except (KeyError, TypeError, ValueError, OverflowError):
                excluded["invalid_anchor_values"] += 1
                continue
            # First complete paired capture only. Later technical improvement
            # cannot reassign this ticker to a more flattering research arm.
            passed = base and vcp and unbroken
            group = ("geometry_pass_" if passed else "geometry_fail_") + (
                "ma_pass" if ma["all_pass"] else "ma_fail")
            first[ticker] = {
                "ticker": ticker, "group": group,
                "observed_at": stamp.isoformat(), "signal_session": session,
                "signalClose": close, "resistance": pivot,
                # Frozen at the first point-in-time observation; never
                # reconstructed from later adjusted historical prices.
                "unbroken_at_capture": unbroken,
                **({
                    "activity_quality_at_capture": asof_activity_quality(row),
                    "swing_concordance_at_capture": asof_swing_concordance(row),
                    "canonical_quality_at_capture": asof_canonical_quality(row),
                } if at_risk_only else {}),
            }
    groups = {name: [] for name in GROUPS}
    # Precommitted, result-independent SHA-256 ordering within one immutable
    # capture prevents the first 32 alphabetical symbols dominating a group.
    # Publication time remains primary: later captures never displace earlier
    # accepted observations. This is a deterministic sample, NOT randomization.
    def same_slot_priority(case):
        key = ("vestra-ma-vcp-2026-v1:" + case["ticker"]).encode("utf-8")
        return hashlib.sha256(key).hexdigest()

    for case in sorted(first.values(), key=lambda x: (x["observed_at"], same_slot_priority(x), x["ticker"])):
        if len(groups[case["group"]]) < per_group:
            groups[case["group"]].append(case)
    return {
        "instrumented_slots_observed": instrumented_slots,
        "instrumented_evaluable_rows_observed": instrumented_evaluable_rows,
        "latest_instrumented_capture": latest_instrumented_capture,
        "capture_readiness": (
            "awaiting_first_instrumented_scan" if not instrumented_slots
            else "awaiting_complete_anchored_observation" if not first
            else "captured_prospective_groups"),
        "groups": groups,
        "eligible_unique_first_observations": dict(sorted(Counter(x["group"] for x in first.values()).items())),
        "excluded_reasons": dict(sorted(excluded.items())),
        "selection_policy": (
            "first_at_risk_prospective_complete_ma_shadow_per_ticker_v2"
            if at_risk_only else "first_complete_prospective_ma_shadow_and_asof_anchor_per_ticker"),
        "at_risk_baseline_only": at_risk_only,
        "not_before_instrumented_utc": AT_RISK_COHORT_START if at_risk_only else None,
        "within_publication_selection_order": "sha256_vestra_ma_vcp_2026_v1_ticker_not_alphabetical",
        "deterministic_sample_not_randomized": True,
        "per_group_budget": per_group,
        "not_all_stocks_or_all_history": True,
    }


def compare(selected: dict, event_prices: dict | None) -> dict:
    result = {
        "schema": ("vestra_prebreakout_ma_geometry_at_risk_forward_v2"
                   if selected.get("at_risk_baseline_only") is True
                   else "vestra_prebreakout_ma_geometry_forward_v1"),
        "baseline_prebreakout_required": selected.get("at_risk_baseline_only") is True,
        "groups": {},
        "horizons_sessions": list(HORIZONS),
        "selection": {k: v for k, v in selected.items() if k != "groups"},
        "research_only": True,
        "point_in_time_membership_not_reconstructed": True,
        "groups_not_randomized_or_matched_on_market_regime": True,
        "independent_predictive_performance_validated": False,
        "calibrated_probability": None,
    }
    for name in GROUPS:
        cases = selected["groups"][name]
        activity_counts = Counter(case.get("activity_quality_at_capture", "unmeasured") for case in cases)
        swing_counts = Counter(case.get("swing_concordance_at_capture", "unmeasured") for case in cases)
        canonical_counts = Counter(case.get("canonical_quality_at_capture", "unmeasured") for case in cases)
        bucket = {
            "selected_tickers": len(cases),
            **({"cross_method_concordance_at_capture": {
                "swing_geometry_counts": dict(sorted(swing_counts.items())),
                "canonical_gate_counts": dict(sorted(canonical_counts.items())),
                "swing_confirmed_and_canonical_passed": sum(
                    case.get("swing_concordance_at_capture") == "swing_geometry_confirmed"
                    and case.get("canonical_quality_at_capture") == "canonical_structural_gates_passed"
                    for case in cases),
                "research_only_descriptive_no_forward_signal_or_cohort_reassignment": True,
            }} if selected.get("at_risk_baseline_only") is True else {}),
            **({"activity_quality_at_capture": {
                "counts": dict(sorted(activity_counts.items())),
                "independently_evaluable_baselines": activity_counts.get(
                    "verified_nonflat_price_and_volume_at_capture", 0),
                "no_posthoc_reassignment_or_replacement": True,
            }} if selected.get("at_risk_baseline_only") is True else {}),
            "baseline_integrity": {
                "unbroken_prebreakout_at_capture": sum(
                    case["unbroken_at_capture"] is True for case in cases),
                "already_broken_or_outside_pivot_at_capture": sum(
                    case["unbroken_at_capture"] is False for case in cases),
                "not_suitable_as_prebreakout_control_if_already_broken": True,
                "fixed_point_in_time_membership_unchanged": True,
            },
            "by_horizon": {
                str(h): {"confirmed_matured": 0, "not_confirmed_matured": 0,
                         "unknown_pending_or_unverified": 0, "unknown_reasons": {}}
                for h in HORIZONS
            },
        }
        for case in cases:
            signal = {
                "ticker": case["ticker"], "date": case["signal_session"],
                "signalClose": case["signalClose"], "resistance": case["resistance"],
                "signalPriceBasis": "yahoo_auto_adjusted_asof_publication",
            }
            snapshot = {
                "schema": "vestra_prebreakout_v1",
                "generated_at": case["observed_at"], "signals": [signal],
            }
            bars = (event_prices or {}).get(case["ticker"])
            for horizon in HORIZONS:
                cell = bucket["by_horizon"][str(horizon)]
                # An already-broken or out-of-pivot instrument is not
                # eligible to measure prediction *before* breakout, even
                # when it belongs to a frozen geometry-fail research arm.
                # Keep the original selected cohort but abstain in metrics.
                if case["unbroken_at_capture"] is False:
                    outcome = {"status": "already_broken_or_outside_pivot_at_capture"}
                elif (selected.get("at_risk_baseline_only") is True
                      and case.get("activity_quality_at_capture")
                      != "verified_nonflat_price_and_volume_at_capture"):
                    outcome = {"status": case.get("activity_quality_at_capture",
                                              "technical_activity_not_measured_at_capture")}
                elif not isinstance(bars, list):
                    outcome = {"status": "independent_ohlcv_unavailable"}
                else:
                    try:
                        outcome = breakout_event(snapshot, case["ticker"], bars, horizon)
                    except (KeyError, ValueError, TypeError, OverflowError):
                        outcome = {"status": "invalid_or_gapped_forward_ohlcv"}
                status = outcome.get("status")
                if outcome.get("horizon_matured") is True and status in ("confirmed", "not_confirmed"):
                    cell[status + "_matured"] += 1
                else:
                    cell["unknown_pending_or_unverified"] += 1
                    reason = status if isinstance(status, str) and status else "unspecified"
                    cell["unknown_reasons"][reason] = cell["unknown_reasons"].get(reason, 0) + 1
        for cell in bucket["by_horizon"].values():
            n = cell["confirmed_matured"] + cell["not_confirmed_matured"]
            cell["matured_evaluable"] = n
            cell["matured_coverage"] = round(n / len(cases), 4) if cases else None
            cell["observed_confirmed_fraction_descriptive"] = (
                round(cell["confirmed_matured"] / n, 4)
                if n >= 30 and n / len(cases) >= 0.8 else None
            )
            cell["probability_calibrated"] = False
        result["groups"][name] = bucket
    captured = sum(bucket["selected_tickers"] for bucket in result["groups"].values())
    matured_at_5 = sum(bucket["by_horizon"]["5"]["matured_evaluable"]
                       for bucket in result["groups"].values())
    if captured == 0:
        result["evidence_readiness"] = result["selection"]["capture_readiness"]
    elif matured_at_5 == 0:
        result["evidence_readiness"] = "captured_awaiting_first_matured_outcome"
    else:
        result["evidence_readiness"] = "maturing_observations_not_calibrated"
    result["matured_5_session_evaluable"] = matured_at_5
    result["selected_tickers_total"] = captured
    return result
