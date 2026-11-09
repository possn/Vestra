#!/usr/bin/env python3
"""Independent freshness gate for *published* smallcap OHLCV research.

Checks the commit actually visible on main, not the collector's workspace.
No provider queries, financial signal scoring or synthetic observations.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parents[1] / "data" / "breakout-lab-smallcap-ohlcv-research.json"
SCHEMA = "vestra_breakout_lab_smallcap_ohlcv_research_v1"


def assess_publication(report: dict, now: datetime, max_age_hours: int = 8) -> dict:
    if now.tzinfo is None or type(max_age_hours) is not int or max_age_hours < 1:
        raise ValueError("UTC-aware now and a positive integer age limit required")
    if not isinstance(report, dict) or report.get("schema") != SCHEMA:
        return {"status": "invalid", "reason": "invalid_schema"}
    try:
        stamp = datetime.fromisoformat(str(report["generated_at"]).replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            return {"status": "invalid", "reason": "naive_generated_at"}
    except (KeyError, ValueError, TypeError):
        return {"status": "invalid", "reason": "invalid_generated_at"}
    age = now.astimezone(timezone.utc) - stamp.astimezone(timezone.utc)
    if age < timedelta(minutes=-5):
        return {"status": "invalid", "reason": "future_generated_at"}
    if age > timedelta(hours=max_age_hours):
        return {"status": "stale", "reason": "publication_age_exceeded",
                "age_hours": round(age.total_seconds() / 3600, 2)}
    rows = report.get("observations")
    total = report.get("universe_100m_500m_count")
    evaluable = report.get("evaluable_ohlcv")
    observed = report.get("distinct_tickers_observed", len(rows) if isinstance(rows, list) else -1)
    if (not isinstance(rows, list) or type(total) is not int or total < 0
        or type(evaluable) is not int or evaluable < 0
        or type(observed) is not int or observed != len(rows)
        or len(rows) > total):
        return {"status": "invalid", "reason": "invalid_coverage_counts"}
    tickers = [row.get("ticker") if isinstance(row, dict) else None for row in rows]
    if any(not isinstance(ticker, str) or not ticker.strip() for ticker in tickers) or len(set(tickers)) != len(tickers):
        return {"status": "invalid", "reason": "duplicate_or_missing_ticker"}
    if evaluable != sum(row.get("status") == "evaluable_ohlcv" for row in rows):
        return {"status": "invalid", "reason": "unreconciled_evaluable_count"}
    if report.get("not_observed") != total - len(rows):
        return {"status": "invalid", "reason": "unreconciled_unobserved_count"}
    incomplete = report.get("observed_incomplete")
    if incomplete is not None and (type(incomplete) is not int or incomplete != len(rows) - evaluable):
        return {"status": "invalid", "reason": "unreconciled_incomplete_count"}
    coverage = report.get("universe_coverage_pct")
    expected = round(100 * evaluable / total, 2) if total else None
    if coverage is not None and (type(coverage) not in (int, float) or coverage != expected):
        return {"status": "invalid", "reason": "unreconciled_coverage_percentage"}
    attempt_counts = report.get("provider_attempt_status_counts")
    if attempt_counts is not None:
        attempted = report.get("provider_tickers_attempted")
        if (not isinstance(attempt_counts, dict)
            or type(attempted) is not int or attempted < 0
            or any(not isinstance(k, str) or not k.strip()
                   or type(v) is not int or v < 0 for k, v in attempt_counts.items())
            or sum(attempt_counts.values()) != attempted
            or attempted > total):
            return {"status": "invalid", "reason": "unreconciled_provider_attempt_counts"}
        error_counts = report.get("provider_error_type_counts")
        if error_counts is not None and (
            not isinstance(error_counts, dict)
            or any(not isinstance(k, str) or not k.strip()
                   or type(v) is not int or v < 0 for k, v in error_counts.items())
            or sum(error_counts.values()) > attempt_counts.get("provider_error", 0)
        ):
            return {"status": "invalid", "reason": "unreconciled_provider_error_types"}
    return {"status": "healthy", "reason": "verified_published_snapshot",
            "age_hours": round(age.total_seconds() / 3600, 2),
            "evaluable": evaluable, "universe": total}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=Path, default=DEFAULT_PATH)
    parser.add_argument("--max-age-hours", type=int, default=8)
    args = parser.parse_args()
    try:
        report = json.loads(args.file.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "invalid", "reason": "missing_or_unreadable_publication",
                          "error_type": type(exc).__name__}))
        return 1
    verdict = assess_publication(report, datetime.now(timezone.utc), args.max_age_hours)
    print(json.dumps(verdict, ensure_ascii=False, sort_keys=True))
    return 0 if verdict["status"] == "healthy" else 1


if __name__ == "__main__":
    raise SystemExit(main())
