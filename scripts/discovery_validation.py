"""Point-in-time *evaluation* of exported Vestra Discovery rankings.

This does NOT reconstruct historical signals or prove an alpha claim. Input must
be independently archived snapshots and subsequently observed total returns.
No live/current fundamentals may be joined back into old snapshots.

CSV columns:
 snapshot_date, signal_asof, ticker, opportunity_score, eligible,
 horizon_sessions, outcome_asof, forward_total_return_pct, benchmark_total_return_pct

Every ticker in each cohort must share the same benchmark and horizon. Outcomes
are total returns in the same currency and over the same measurement interval.
Only complete, mature, distinct cohorts enter the statistics.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
import statistics
from collections import defaultdict

REQUIRED = (
    "snapshot_date", "signal_asof", "ticker", "opportunity_score",
    "eligible", "horizon_sessions", "outcome_asof",
    "forward_total_return_pct", "benchmark_total_return_pct",
)
ALLOWED_HORIZONS = {20, 60, 120, 252}


def _date(value):
    return dt.date.fromisoformat(str(value))


def _number(value):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("Non-finite number")
    return result


def _ranks(values):
    """Average ranks for ties, ascending."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    result = [0.0] * len(values)
    cursor = 0
    while cursor < len(order):
        end = cursor + 1
        while end < len(order) and values[order[end]] == values[order[cursor]]:
            end += 1
        rank = (cursor + 1 + end) / 2.0
        for j in range(cursor, end):
            result[order[j]] = rank
        cursor = end
    return result


def _spearman(xs, ys):
    if len(xs) < 3:
        return None
    a, b = _ranks(xs), _ranks(ys)
    am, bm = statistics.mean(a), statistics.mean(b)
    numerator = sum((x - am) * (y - bm) for x, y in zip(a, b))
    denominator = math.sqrt(sum((x - am) ** 2 for x in a) * sum((y - bm) ** 2 for y in b))
    return numerator / denominator if denominator else None


def evaluate(rows, *, min_cohort=4, min_dates=2):
    """Return diagnostics; fail closed on invalid or incomplete input.

    Mean excess is an equal-weighted, cohort-level *descriptive* statistic,
    not an executable portfolio return, compounded strategy or forecast.
    """
    cohorts = defaultdict(list)
    seen = set()
    for position, row in enumerate(rows, 1):
        missing = [key for key in REQUIRED if key not in row or str(row[key]).strip() == ""]
        if missing:
            raise ValueError(f"Row {position}: missing {', '.join(missing)}")
        try:
            snap = _date(row["snapshot_date"])
            signal = _date(row["signal_asof"])
            outcome = _date(row["outcome_asof"])
            horizon = int(row["horizon_sessions"])
            score = _number(row["opportunity_score"])
            realised = _number(row["forward_total_return_pct"])
            benchmark = _number(row["benchmark_total_return_pct"])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Row {position}: malformed date/number: {exc}") from exc
        if not (signal <= snap < outcome):
            raise ValueError(f"Row {position}: point-in-time violation: signal <= snapshot < outcome required")
        if horizon not in ALLOWED_HORIZONS:
            raise ValueError(f"Row {position}: unsupported trading-session horizon")
        if not 0 <= score <= 100:
            raise ValueError(f"Row {position}: score outside 0..100")
        if str(row["eligible"]).lower().strip() not in ("true", "false"):
            raise ValueError(f"Row {position}: eligible must be true or false")
        ticker = str(row["ticker"]).strip().upper()
        if not ticker:
            raise ValueError(f"Row {position}: empty ticker")
        key = (snap, horizon, ticker)
        if key in seen:
            raise ValueError(f"Row {position}: duplicate snapshot/horizon/ticker {key}")
        seen.add(key)
        if str(row["eligible"]).lower().strip() == "true":
            cohorts[(snap, horizon)].append((ticker, score, realised, benchmark, outcome))

    by_horizon = defaultdict(list)
    discarded = defaultdict(int)
    for (date, horizon), group in sorted(cohorts.items()):
        if len(group) < min_cohort:
            discarded[horizon] += 1
            continue
        benchmarks = [item[3] for item in group]
        if max(benchmarks) - min(benchmarks) > 1e-6:
            raise ValueError(f"{date}/{horizon}: benchmark must be identical across cohort")
        # All values are from a complete eligible universe in the archived snapshot.
        top_n = max(1, math.ceil(len(group) * .25))
        ranked = sorted(group, key=lambda v: (-v[1], v[0]))
        chosen = ranked[:top_n]
        top_mean = statistics.mean(r[2] for r in chosen)
        universe_mean = statistics.mean(r[2] for r in group)
        bench = benchmarks[0]
        ic = _spearman([r[1] for r in group], [r[2] for r in group])
        by_horizon[horizon].append({
            "snapshot_date": str(date), "n": len(group), "top_n": top_n,
            "top_mean_pct": top_mean, "universe_mean_pct": universe_mean,
            "benchmark_pct": bench, "top_minus_universe_pp": top_mean - universe_mean,
            "top_minus_benchmark_pp": top_mean - bench,
            "top_hit_rate": sum(r[2] > bench for r in chosen) / len(chosen),
            "rank_ic": ic,
        })

    report = {"status": "insufficient_history", "horizons": {}, "warnings": [
        "Requires independently captured point-in-time data, inclusive of delisted companies.",
        "No transaction costs, slippage, turnover, capacity or overlapping-position modelling.",
        "Descriptive results are not a validated trading strategy or predicted returns.",
    ]}
    for horizon in sorted(set(by_horizon) | set(discarded)):
        periods = by_horizon[horizon]
        if len(periods) < min_dates:
            report["horizons"][str(horizon)] = {
                "status": "insufficient_history", "valid_dates": len(periods),
                "discarded_small_cohorts": discarded[horizon],
            }
            continue
        def avg(field):
            return round(statistics.mean(p[field] for p in periods), 4)
        ics = [p["rank_ic"] for p in periods if p["rank_ic"] is not None]
        report["horizons"][str(horizon)] = {
            "status": "descriptive_only", "valid_dates": len(periods),
            "discarded_small_cohorts": discarded[horizon],
            "top_minus_universe_pp": avg("top_minus_universe_pp"),
            "top_minus_benchmark_pp": avg("top_minus_benchmark_pp"),
            "top_hit_rate": avg("top_hit_rate"),
            "rank_ic_mean": round(statistics.mean(ics), 4) if ics else None,
        }
        report["status"] = "descriptive_only"
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_file", help="Point-in-time discovery evaluation CSV")
    parser.add_argument("--min-cohort", type=int, default=4)
    parser.add_argument("--min-dates", type=int, default=2)
    args = parser.parse_args()
    if args.min_cohort < 4 or args.min_dates < 2:
        parser.error("min-cohort must be >=4 and min-dates >=2")
    with open(args.csv_file, newline="", encoding="utf-8-sig") as file:
        rows = list(csv.DictReader(file))
    print(json.dumps(evaluate(rows, min_cohort=args.min_cohort, min_dates=args.min_dates),
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
