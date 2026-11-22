#!/usr/bin/env python3
"""Prospective research-only comparison of archived pre-breakout negative controls.

No historical candidate inference: every label and pivot is frozen in a
previously published scanner slot. A reconstructed provider history must first
reconcile the original same-session adjusted anchor; otherwise abstain.
"""
from __future__ import annotations
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from prebreakout_forward_events import breakout_event

GROUPS = ("canonical_structural_pass", "geometry_pass_ma_rejected", "geometry_negative_control")
HORIZONS = (5, 10, 20, 60)

def archived_cases(archive: Path, per_group: int = 16) -> dict:
    if type(per_group) is not int or not 1 <= per_group <= 100:
        raise ValueError("invalid per-group download budget")
    first = {}
    rejected = Counter()
    for path in sorted(archive.glob("*/slots/*-slot*.json")):
        try:
            feed = json.loads(path.read_text(encoding="utf-8"))
            stamp = datetime.fromisoformat(str(feed["generated_at"]).replace("Z", "+00:00"))
            if stamp.tzinfo is None or feed.get("schema") != "vestra_prebreakout_v1":
                continue
            stamp = stamp.astimezone(timezone.utc)
            slot = feed.get("scan_slot_utc")
            if type(slot) is not int or slot != stamp.hour // 6 or path.name != f"{stamp.date().isoformat()}-slot{slot}.json":
                continue
            block = feed.get("research_observations")
            if not isinstance(block, dict) or block.get("point_in_time_capture_not_historical_reconstruction") is not True:
                continue
            rows = block.get("rows")
            if not isinstance(rows, list):
                continue
        except (OSError, KeyError, ValueError, TypeError):
            continue
        seen = set()
        for row in rows:
            if not isinstance(row, dict):
                continue
            ticker = row.get("ticker")
            if not isinstance(ticker, str) or not ticker or len(ticker) > 20 or ticker in seen:
                rejected["invalid_or_duplicate_ticker_in_slot"] += 1
                continue
            seen.add(ticker)
            if ticker in first or row.get("evaluable") is not True:
                continue
            anchor = row.get("asof_base_price_anchor")
            geometry = row.get("geometry_shadow")
            lineage = row.get("research_prebreakout_lineage")
            if not all(isinstance(x, dict) for x in (anchor, geometry, lineage)):
                rejected["missing_capture"] += 1
                continue
            if (anchor.get("schema") != "vestra_prebreakout_asof_base_anchor_v1"
                or anchor.get("historical_adjustment_factor_verified") is not False
                or anchor.get("research_only_no_eligibility_or_score_effect") is not True
                or anchor.get("window_bars") != 40 or anchor.get("reference_bars") != 39):
                rejected["unverifiable_anchor"] += 1
                continue
            base, vcp, unbroken = (geometry.get("base_width_pass"),
                                  geometry.get("contractions_pass"),
                                  lineage.get("unbroken_prebreakout_position"))
            if any(type(x) is not bool for x in (base, vcp, unbroken)):
                rejected["unverifiable_geometry"] += 1
                continue
            first_rejection = row.get("first_rejection")
            if not isinstance(first_rejection, str):
                continue
            if first_rejection == "passed_structural_gates":
                group = GROUPS[0]
            elif base and vcp and unbroken and first_rejection == "moving_average_structure":
                group = GROUPS[1]
            elif not base and not vcp and unbroken:
                group = GROUPS[2]
            else:
                rejected["outside_predeclared_groups"] += 1
                continue
            try:
                session = str(anchor["session"])
                if session != row.get("last_session") or session > stamp.date().isoformat():
                    raise ValueError("future or mismatched session")
                price = float(anchor["adjusted_close"])
                pivot = float(anchor["adjusted_pivot_high"])
                if not (0 < price <= pivot and pivot < float("inf")):
                    raise ValueError("invalid price anchor")
            except (ValueError, KeyError, TypeError, OverflowError):
                rejected["invalid_anchor_values"] += 1
                continue
            first[ticker] = {"ticker": ticker, "group": group,
                             "observed_at": stamp.isoformat(),
                             "signal_session": session,
                             "signalClose": price, "resistance": pivot,
                             "anchor_fingerprint": anchor.get("closed_bar_snapshot_sha256")}
    groups = {name: [] for name in GROUPS}
    for case in sorted(first.values(), key=lambda x: (x["observed_at"], x["ticker"])):
        group = groups[case["group"]]
        if len(group) < per_group:
            group.append(case)
    return {"groups": groups, "available_unique_first_observations":
            dict(Counter(c["group"] for c in first.values())),
            "excluded_reasons": dict(rejected),
            "selection_policy": "first_valid_original_publication_per_ticker_earliest_per_group",
            "per_group_budget": per_group,
            "full_universe_not_claimed": True}

def compare(archive: Path, event_prices: dict | None, per_group: int = 16) -> dict:
    selected = archived_cases(archive, per_group=per_group)
    report = {"schema": "vestra_prebreakout_negative_controls_forward_v1",
              "method": "original_published_adjusted_pivot_reconciled_forward_event",
              "groups": {}, "selection": {key: value for key, value in selected.items() if key != "groups"},
              "horizons_sessions": list(HORIZONS),
              "research_only": True, "out_of_sample_validated": False,
              "selection_effect_validated": False, "calibrated_probabilities": None}
    for name in GROUPS:
        cases = selected["groups"][name]
        bucket = {"selected_tickers": len(cases),
                  "by_horizon": {str(h): {"confirmed_matured": 0, "not_confirmed_matured": 0,
                                         "unknown_pending_or_unverified": 0,
                                         "unknown_reasons": {}} for h in HORIZONS}}
        for case in cases:
            # Synthetic wrapper only; pivot and signalClose come unchanged from
            # the immutable as-of capture, NOT reconstructed from latest prices.
            signal = {"ticker": case["ticker"], "date": case["signal_session"],
                      "signalClose": case["signalClose"], "resistance": case["resistance"],
                      "signalPriceBasis": "yahoo_auto_adjusted_asof_publication"}
            snapshot = {"schema": "vestra_prebreakout_v1", "generated_at": case["observed_at"],
                        "signals": [signal]}
            bars = (event_prices or {}).get(case["ticker"])
            for h in HORIZONS:
                cell = bucket["by_horizon"][str(h)]
                if not isinstance(bars, list):
                    outcome = {"status": "independent_ohlcv_unavailable"}
                else:
                    try:
                        outcome = breakout_event(snapshot, case["ticker"], bars, h)
                    except (ValueError, KeyError, TypeError, OverflowError):
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
            # Correlated names and time periods; no precision/recall estimate
            # or trained classifier until independent future episodes exist.
            cell["observed_confirmed_fraction_descriptive"] = (
                round(cell["confirmed_matured"] / n, 4) if n >= 30
                and len(cases) > 0 and n / len(cases) >= 0.8 else None)
            cell["probability_calibrated"] = False
        report["groups"][name] = bucket
    return report
