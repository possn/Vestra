#!/usr/bin/env python3
"""Bounded historical market turning features; descriptive research only.

Yahoo adjusted histories retrieved today are NOT original archived point-in-
time vintages. Do not use this report for calibrated probability claims.
"""
from __future__ import annotations
import argparse
import json
import math
from datetime import date, datetime, timezone
from pathlib import Path
from market_turning_feature_lab import lab_report
from market_turning_walkforward import evaluate
from market_turning_conditional_ablations import conditional_evaluate

ROOT = Path(__file__).resolve().parents[1]
SYMBOLS = ("SPY", "^VIX", "^VVIX", "^COR1M", "^VIX3M", "HYG", "LQD")


def normalize_yahoo(frame, before):
    """Retain completed daily observations only; no bar interpolation."""
    if frame is None or getattr(frame, "empty", True):
        return []
    if "Close" not in frame.columns:
        return []
    rows = []
    seen = set()
    for stamp, data in frame.iterrows():
        try:
            day = stamp.date()
            if day >= before:
                continue
            close = float(data["Close"])
            if day in seen or not math.isfinite(close) or close <= 0:
                return []
            seen.add(day)
            row = {"date": day.isoformat(), "close": close}
            for col, key in (("High", "high"), ("Low", "low"), ("Volume", "volume")):
                if col in frame.columns:
                    try:
                        value = float(data[col])
                        if math.isfinite(value):
                            row[key] = value
                    except (ValueError, TypeError, OverflowError):
                        pass
            rows.append(row)
        except (ValueError, TypeError, OverflowError, AttributeError):
            return []
    return sorted(rows, key=lambda row: row["date"])


def collect(downloader, now=None, start="2004-01-01"):
    """Independent calls per symbol with bounded same-source retry."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("timezone-aware clock required")
    before = now.astimezone(timezone.utc).date()
    prices, failures = {}, {}
    for ticker in SYMBOLS:
        rows = []
        for attempt in (1, 2):
            try:
                frame = downloader(ticker, start=start,
                    end=before.isoformat(), auto_adjust=True,
                    progress=False, threads=False, multi_level_index=False)
                rows = normalize_yahoo(frame, before)
                if rows:
                    break
            except Exception as exc:
                failures[ticker] = type(exc).__name__
        prices[ticker] = rows
        if not rows:
            failures.setdefault(ticker, "missing_or_invalid_completed_bars")
    if len(prices["SPY"]) < 750:
        raise ValueError("SPY history insufficient for long-horizon research")
    result = lab_report(prices)
    # Exploratory chronological benchmark; retrospective provider vintages remain unverified.
    result["holdout"] = evaluate(prices)
    # Distinguish recognition of drawdown from prospective turning-point skill.
    result["stress_conditioned_ablation"] = conditional_evaluate(prices)
    result["generated_at"] = now.isoformat()
    result["source_provenance"] = {
        "provider": "yahoo_finance",
        "adjusted_historical_ohlcv_retrieved_now": True,
        "point_in_time_original_vintage_verified": False,
        "completed_before_utc_date": before.isoformat(),
        "requested_start": start,
        "optional_symbol_failures": failures,
        "historical_reference": "descriptive_candidate_feature_coverage_only",
        "never_promote_report_to_live_probability_or_risk_gate": True,
    }
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path,
                   default=ROOT / "data/market-turning-feature-lab.json")
    p.add_argument("--start", default="2004-01-01")
    args = p.parse_args()
    import yfinance as yf
    result = collect(yf.download, start=args.start)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, allow_nan=False,
                                     ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print("Historical research features:", result["sample"]["rows"],
          "sessions; NOT calibrated turning probabilities")


if __name__ == "__main__":
    main()
