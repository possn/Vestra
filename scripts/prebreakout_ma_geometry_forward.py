#!/usr/bin/env python3
"""Prospective, frozen four-arm MA x VCP forward comparison; research only.

The first *eligible capture after the MA-shadow schema exists* per ticker fixes
group membership. Never relabel the first capture after observing outcomes.
Missing/incomplete price evidence remains unknown, not an unsuccessful signal.
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime, timezone
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


def select(archive: Path, per_group: int = 32) -> dict:
    if type(per_group) is not int or not 1 <= per_group <= 100:
        raise ValueError("invalid predeclared research cohort budget")
    first = {}
    excluded = Counter()
    for path in sorted(archive.glob("*/slots/*-slot*.json")):
        try:
            snapshot = json.loads(path.read_text(encoding="utf-8"))
            stamp = datetime.fromisoformat(snapshot["generated_at"].replace("Z", "+00:00"))
            if (stamp.tzinfo is None or snapshot.get("schema") != "vestra_prebreakout_v1"):
                continue
            stamp = stamp.astimezone(timezone.utc)
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
            }
    groups = {name: [] for name in GROUPS}
    for case in sorted(first.values(), key=lambda x: (x["observed_at"], x["ticker"])):
        if len(groups[case["group"]]) < per_group:
            groups[case["group"]].append(case)
    return {
        "groups": groups,
        "eligible_unique_first_observations": dict(sorted(Counter(x["group"] for x in first.values()).items())),
        "excluded_reasons": dict(sorted(excluded.items())),
        "selection_policy": "first_complete_prospective_ma_shadow_and_asof_anchor_per_ticker",
        "per_group_budget": per_group,
        "not_all_stocks_or_all_history": True,
    }


def compare(selected: dict, event_prices: dict | None) -> dict:
    result = {
        "schema": "vestra_prebreakout_ma_geometry_forward_v1",
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
        bucket = {
            "selected_tickers": len(cases),
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
                if not isinstance(bars, list):
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
    return result
