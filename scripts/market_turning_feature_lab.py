#!/usr/bin/env python3
"""Read-only market-turning feature laboratory. No probabilities or trading signals.

Input JSON maps tickers to dated completed daily observations. This module does
not download prices, fill gaps, mutate published scores, or infer unavailable
volume, credit, breadth, or options data. Future outcomes are used ONLY for
research labels and never by the as-of feature extractor.
"""
from __future__ import annotations
import argparse
import json
import math
from datetime import date, timedelta
from pathlib import Path

FEATURES = (
    "rsi_daily_5", "rsi_daily_14", "rsi_weekly_14",
    "mfi_daily_14", "drawdown_126_pct", "ma50_gap_pct",
    "vix_percentile_126", "vvix_percentile_126",
    "cor1m_percentile_126", "vix_1m_3m_ratio",
    "hyg_lqd_change_5_pct",
)


def series(raw, ticker):
    """Require strictly ordered dates; never interpolate or silently discard."""
    rows = raw.get(ticker)
    if not isinstance(rows, list):
        return []
    result = []
    last = ""
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("date"), str):
            raise ValueError(f"{ticker}: invalid date")
        day = row["date"]
        try:
            parsed = date.fromisoformat(day)
        except ValueError as exc:
            raise ValueError(f"{ticker}: invalid ISO date") from exc
        if parsed.isoformat() != day or day <= last:
            raise ValueError(f"{ticker}: unsorted or duplicate date")
        last = day
        close = row.get("close")
        if type(close) not in (int, float) or not math.isfinite(close) or close <= 0:
            raise ValueError(f"{ticker}: invalid close")
        normalized = {"date": day, "close": float(close)}
        for name in ("high", "low", "volume"):
            value = row.get(name)
            if type(value) in (int, float) and math.isfinite(value):
                normalized[name] = float(value)
        result.append(normalized)
    return result


def rsi(closes, period=14):
    """Wilder's smoothed RSI, causal and correctly seeded."""
    if len(closes) < period + 1:
        return None
    changes = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = sum(max(x, 0) for x in changes[:period]) / period
    losses = sum(max(-x, 0) for x in changes[:period]) / period
    for movement in changes[period:]:
        gains = (gains * (period - 1) + max(movement, 0)) / period
        losses = (losses * (period - 1) + max(-movement, 0)) / period
    if gains == 0 and losses == 0:
        return 50.0
    if losses == 0:
        return 100.0
    return 100 - 100 / (1 + gains / losses)


def mfi(rows, period=14):
    """Quong/Soudack MFI; requires actual ETF high/low/close/volume."""
    if len(rows) < period + 1:
        return None
    chosen = rows[-period - 1:]
    typical = []
    for row in chosen:
        h, l, c, v = (row.get(k) for k in ("high", "low", "close", "volume"))
        if (not all(type(x) in (int, float) and math.isfinite(x) for x in (h, l, c, v))
                or not 0 < l <= c <= h or v <= 0):
            return None
        typical.append(((h + l + c) / 3, v))
    positive = negative = 0.0
    for (previous, _), (current, volume) in zip(typical, typical[1:]):
        money = current * volume
        if current > previous:
            positive += money
        elif current < previous:
            negative += money
    if positive == 0 and negative == 0:
        return 50.0
    if negative == 0:
        return 100.0
    return 100 * positive / (positive + negative)


def closed_weekly_closes(rows, asof):
    """Only weeks definitely closed by the as-of daily candle are eligible."""
    day = date.fromisoformat(asof)
    weeks = {}
    for row in rows:
        current = date.fromisoformat(row["date"])
        monday = current - timedelta(days=current.weekday())
        friday = monday + timedelta(days=4)
        if friday <= day and current <= day:
            weeks[monday.isoformat()] = row["close"]
    return list(weeks.values())


def percentile(rows, asof, window=126):
    prior = [r for r in rows if r["date"] <= asof]
    if len(prior) < window or prior[-1]["date"] != asof:
        return None
    levels = [r["close"] for r in prior[-window:]]
    return 100 * sum(v <= levels[-1] for v in levels) / window


def same_day(rows, asof):
    eligible = [row for row in rows if row["date"] <= asof]
    return eligible if eligible and eligible[-1]["date"] == asof else []


def feature_row(histories, asof):
    """Computes an as-of vector using no bars after asof, even if supplied."""
    spy = same_day(histories.get("SPY", []), asof)
    if len(spy) < 50:
        return None
    closes = [x["close"] for x in spy]
    last = closes[-1]
    h126 = max(closes[-126:]) if len(closes) >= 126 else None
    ma50 = sum(closes[-50:]) / 50
    result = {key: None for key in FEATURES}
    result.update({
        "rsi_daily_5": rsi(closes, 5),
        "rsi_daily_14": rsi(closes, 14),
        "rsi_weekly_14": rsi(closed_weekly_closes(spy, asof), 14),
        "mfi_daily_14": mfi(spy, 14),
        "drawdown_126_pct": 100 * (last / h126 - 1) if h126 else None,
        "ma50_gap_pct": 100 * (last / ma50 - 1),
    })
    for ticker, key in (
        ("^VIX", "vix_percentile_126"),
        ("^VVIX", "vvix_percentile_126"),
        ("^COR1M", "cor1m_percentile_126"),
    ):
        result[key] = percentile(histories.get(ticker, []), asof)
    vix = same_day(histories.get("^VIX", []), asof)
    vix3m = same_day(histories.get("^VIX3M", []), asof)
    if vix and vix3m:
        result["vix_1m_3m_ratio"] = vix[-1]["close"] / vix3m[-1]["close"]
    hyg = same_day(histories.get("HYG", []), asof)
    lqd = same_day(histories.get("LQD", []), asof)
    if len(hyg) >= 6 and len(lqd) >= 6:
        lqd_by_day = {x["date"]: x["close"] for x in lqd}
        paired = [(x["date"], x["close"] / lqd_by_day[x["date"]])
                  for x in hyg if x["date"] in lqd_by_day]
        if len(paired) >= 6 and paired[-1][0] == asof:
            result["hyg_lqd_change_5_pct"] = 100 * (paired[-1][1] / paired[-6][1] - 1)
    return result


def future_reversal_labels(spy, index, forward=20, nearby=5,
                           min_drawdown=0.07, min_rebound=0.05):
    """Research outcomes require future maturity; no use in feature_row().

    Label a nearby bottom only when a preceding drawdown is material, an
    extreme lies in the next 5 sessions and it rebounds by 5% within 20.
    The top is defined symmetrically with prior run-up and future decline.
    These thresholds are predeclared *research* definitions, not optimized.
    """
    if index < 125 or index + forward >= len(spy):
        return {"bottom": None, "top": None}
    closes = [row["close"] for row in spy]
    last = closes[index]
    past = closes[index - 125:index + 1]
    future = closes[index:index + forward + 1]
    initial = future[:nearby + 1]
    low = min(initial)
    low_at = initial.index(low)
    high = max(initial)
    high_at = initial.index(high)
    rebound = max(future[low_at:]) / low - 1
    reversal = 1 - min(future[high_at:]) / high
    # Reject false bottoms that quickly make substantially lower lows.
    failed_low = min(future[nearby + 1:]) < low * 0.99
    failed_high = max(future[nearby + 1:]) > high * 1.01
    return {
        "bottom": bool((1 - last / max(past)) >= min_drawdown
                       and rebound >= min_rebound and not failed_low),
        "top": bool((last / min(past) - 1) >= min_drawdown
                    and reversal >= min_rebound and not failed_high),
    }


def pearson(x, y):
    if len(x) < 10 or len(x) != len(y):
        return None
    mx, my = sum(x) / len(x), sum(y) / len(y)
    sx = sum((v - mx) ** 2 for v in x)
    sy = sum((v - my) ** 2 for v in y)
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / math.sqrt(sx * sy) if sx > 0 and sy > 0 else None


def lab_report(raw, max_rows=None):
    histories = {k: series(raw, k) for k in ("SPY", "^VIX", "^VVIX",
                  "^COR1M", "^VIX3M", "HYG", "LQD")}
    spy = histories["SPY"]
    if len(spy) < 150:
        raise ValueError("require at least 150 completed daily SPY rows")
    observations = []
    for i in range(125, len(spy)):
        asof = spy[i]["date"]
        values = feature_row(histories, asof)
        if values is None:
            continue
        observations.append({
            "date": asof, "features": values,
            "label": future_reversal_labels(spy, i),
        })
    if max_rows is not None:
        observations = observations[-max_rows:]
    coverage = {}
    for k in FEATURES:
        valid = sum(v["features"][k] is not None for v in observations)
        coverage[k] = {"observed": valid, "total": len(observations),
                       "pct": round(100 * valid / len(observations), 2) if observations else None}
    relations = []
    for i, first in enumerate(FEATURES):
        for second in FEATURES[i + 1:]:
            pairs = [(o["features"][first], o["features"][second])
                     for o in observations if o["features"][first] is not None
                     and o["features"][second] is not None]
            r = pearson([p[0] for p in pairs], [p[1] for p in pairs])
            if r is not None:
                relations.append({"first": first, "second": second, "n": len(pairs),
                                  "pearson_descriptive": round(r, 4)})
    labels = {side: {
        "matured": sum(o["label"][side] is not None for o in observations),
        "events": sum(o["label"][side] is True for o in observations),
    } for side in ("bottom", "top")}
    outcome_associations = {"bottom": [], "top": []}
    for side in ("bottom", "top"):
        for feature in FEATURES:
            paired = [(o["features"][feature], int(o["label"][side]))
                      for o in observations
                      if o["label"][side] is not None
                      and o["features"][feature] is not None]
            coefficient = pearson([p[0] for p in paired], [p[1] for p in paired])
            if coefficient is not None:
                outcome_associations[side].append({
                    "feature": feature,
                    "n_correlated_sessions_not_independent_episodes": len(paired),
                    "point_biserial_exploratory": round(coefficient, 4),
                    "not_out_of_sample_or_causal_evidence": True,
                })
    return {
        "schema": "vestra_market_turning_feature_lab_v1",
        "research_only": True, "probability_calibrated": False,
        "score_or_live_vote_changed": False,
        "method": "completed_asof_spy_daily_ohlcv_optional_independent_series",
        "labels": {"nearby_sessions": 5, "future_sessions": 20,
                   "prior_drawdown_or_runup": 0.07, "rebound_or_reversal": 0.05,
                   "research_definition_not_proven_event_ground_truth": True},
        "sample": {"rows": len(observations), "first": observations[0]["date"] if observations else None,
                   "last": observations[-1]["date"] if observations else None},
        "event_counts_descriptive_not_independent": labels,
        "feature_coverage": coverage, "feature_correlations_descriptive_not_validation": relations,
        "outcome_associations_in_sample_exploratory": outcome_associations,
        "model_probability": None,
        "holdout": {"evaluated": False, "reason": "no_purged_walkforward_or_probability_calibration_yet"},
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, required=True, help="independently sourced completed daily OHLCV JSON")
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    raw = json.loads(args.input.read_text(encoding="utf-8"))
    result = lab_report(raw)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                           encoding="utf-8")
    print(f"Research-only market turning features: {result['sample']['rows']} as-of sessions")


if __name__ == "__main__":
    main()
