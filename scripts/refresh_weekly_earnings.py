#!/usr/bin/env python3
"""Refresh near-term company earnings results in the lightweight startup payload.

The Dashboard weekly calendar is rendered from data/stocks-startup.json. The
canonical market build intentionally strips most analyst detail from that file,
so a reported quarter can otherwise remain displayed as "pending" until the
next full market build. This refresher updates only companies with an earnings
catalyst close to today and preserves the last verified values on network
failure.
"""
from __future__ import annotations

import json
import math
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "data" / "stocks-index.json"
STARTUP = ROOT / "data" / "stocks-startup.json"
MAX_STARTUP_BYTES = 2_350_000
EXCLUDED_TYPES = {"ETF", "FUND", "MUTUALFUND", "CRYPTO"}

RESULT_FIELDS = (
    "analyst_eps_next_q",
    "analyst_next_earnings_date",
    "analyst_latest_earnings_date",
    "analyst_latest_eps_estimate",
    "analyst_latest_eps_actual",
    "analyst_latest_eps_surprise_pct",
)


def _number(value):
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _calendar_date(value):
    raw = str(value or "").strip()[:10]
    try:
        return date.fromisoformat(raw)
    except Exception:
        return None


def _row_value(row, names):
    for name in names:
        try:
            if name in row.index:
                value = row.get(name)
                if value is not None:
                    return value
        except Exception:
            pass
    return None


def candidate_tickers(payload: dict, today: date | None = None, past_days: int = 10, future_days: int = 14) -> list[str]:
    today = today or date.today()
    start = today - timedelta(days=past_days)
    end = today + timedelta(days=future_days)
    out = []
    for row in payload.get("stocks") or []:
        if not isinstance(row, dict):
            continue
        ticker = str(row.get("ticker") or "").strip().upper()
        quote_type = str(row.get("quote_type") or "").strip().upper()
        if not ticker or quote_type in EXCLUDED_TYPES:
            continue
        dates = (
            _calendar_date(row.get("analyst_next_earnings_date")),
            _calendar_date(row.get("analyst_latest_earnings_date")),
        )
        if any(value is not None and start <= value <= end for value in dates):
            out.append(ticker)
    return sorted(set(out))


def _as_utc_datetime(value):
    try:
        dt = value.to_pydatetime() if hasattr(value, "to_pydatetime") else value
        if not isinstance(dt, datetime):
            dt = datetime.fromisoformat(str(value))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def extract_snapshot(earnings_dates, earnings_estimate=None, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    out: dict[str, Any] = {}

    # Forward consensus used by the not-yet-reported event card.
    try:
        if earnings_estimate is not None and not getattr(earnings_estimate, "empty", True):
            if "+1q" in earnings_estimate.index and "avg" in earnings_estimate.columns:
                value = _number(earnings_estimate.loc["+1q", "avg"])
                if value is not None:
                    out["analyst_eps_next_q"] = value
    except Exception:
        pass

    if earnings_dates is None or getattr(earnings_dates, "empty", True):
        return out

    reported_rows = []
    future_rows = []
    for idx, row in earnings_dates.iterrows():
        dt = _as_utc_datetime(idx)
        if dt is None:
            continue
        actual = _number(_row_value(row, ("Reported EPS", "reportedEPS", "epsActual")))
        estimate = _number(_row_value(row, ("EPS Estimate", "epsEstimate", "epsEstimateCurrent")))
        surprise = _number(_row_value(row, ("Surprise(%)", "surprisePercent", "surprisePct")))
        # Yahoo/yfinance exposes this field as a percentage (for example 0.71
        # means +0.71%), while Vestra stores it as a decimal fraction because
        # the Dashboard multiplies the stored value by 100 for presentation.
        if surprise is not None:
            surprise /= 100.0
        if surprise is None and actual is not None and estimate not in (None, 0):
            surprise = actual / estimate - 1.0
        item = (dt, actual, estimate, surprise)
        if actual is not None and dt <= now + timedelta(days=1):
            reported_rows.append(item)
        elif actual is None and dt >= now - timedelta(days=1):
            future_rows.append(item)

    if reported_rows:
        dt, actual, estimate, surprise = max(reported_rows, key=lambda item: item[0])
        out["analyst_latest_earnings_date"] = dt.date().isoformat()
        out["analyst_latest_eps_actual"] = actual
        if estimate is not None:
            out["analyst_latest_eps_estimate"] = estimate
        if surprise is not None:
            out["analyst_latest_eps_surprise_pct"] = surprise

    if future_rows:
        dt, _actual, estimate, _surprise = min(future_rows, key=lambda item: item[0])
        out["analyst_next_earnings_date"] = dt.date().isoformat()
        if out.get("analyst_eps_next_q") is None and estimate is not None:
            out["analyst_eps_next_q"] = estimate
    elif reported_rows:
        # Remove a stale "next" date that is the quarter just reported. The
        # Dashboard will then show the reported event only once.
        out["analyst_next_earnings_date"] = None

    return out


def fetch_snapshot(ticker: str) -> dict[str, Any]:
    import yfinance as yf

    company = yf.Ticker(ticker)
    try:
        earnings_dates = company.get_earnings_dates(limit=16)
    except Exception:
        earnings_dates = None
    try:
        earnings_estimate = company.get_earnings_estimate()
    except Exception:
        earnings_estimate = None
    return extract_snapshot(earnings_dates, earnings_estimate)


def apply_snapshot(row: dict, snapshot: dict) -> bool:
    changed = False
    for key in RESULT_FIELDS:
        if key not in snapshot:
            continue
        value = snapshot[key]
        if row.get(key) != value:
            row[key] = value
            changed = True
    return changed


def pack_index_payload(index_payload: dict) -> dict:
    rows = index_payload.get("stocks") or []
    frequency: dict[str, int] = defaultdict(int)
    for row in rows:
        if isinstance(row, dict):
            for key in row:
                frequency[key] += 1
    fields = sorted(frequency, key=lambda key: (-frequency[key], key))
    packed_rows = []
    for row in rows:
        values = [row.get(field) if field in row else None for field in fields]
        while values and values[-1] is None:
            values.pop()
        packed_rows.append(values)
    meta = {key: value for key, value in index_payload.items() if key != "stocks"}
    return {**meta, "layout": "field_rows_v1", "fields": fields, "rows": packed_rows}


def main() -> int:
    payload = json.loads(INDEX.read_text(encoding="utf-8"))
    rows = payload.get("stocks") or []
    by_ticker = {str(row.get("ticker") or "").strip().upper(): row for row in rows if isinstance(row, dict)}
    candidates = candidate_tickers(payload)
    attempted = matched = updated = 0
    failures = []
    for ticker in candidates[:80]:
        attempted += 1
        try:
            snapshot = fetch_snapshot(ticker)
        except Exception as exc:
            failures.append(f"{ticker}:{type(exc).__name__}")
            continue
        if not snapshot:
            continue
        matched += 1
        row = by_ticker.get(ticker)
        if row is not None and apply_snapshot(row, snapshot):
            updated += 1

    packed = pack_index_payload(payload)
    encoded = json.dumps(packed, ensure_ascii=False, separators=(",", ":")) + "\n"
    if len(encoded.encode("utf-8")) > MAX_STARTUP_BYTES:
        raise RuntimeError("weekly earnings refresh would exceed startup payload budget")

    INDEX.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    STARTUP.write_text(encoded, encoding="utf-8")
    print(json.dumps({
        "state": "checked",
        "candidate_count": len(candidates),
        "attempted": attempted,
        "matched": matched,
        "updated": updated,
        "failures": failures[:10],
        "contract": "near-term earnings only; preserve last verified values on fetch failure",
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
