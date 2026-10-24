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
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
import sys

# The earnings workflow executes regression tests as `python tests/...`.
# In that mode neither the repository root nor scripts/ is on sys.path.
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
from build_market_shards import _compact_startup_value, MAX_COLUMNAR_BYTES
from earnings_archive import save_archive

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "data" / "stocks-index.json"
STARTUP = ROOT / "data" / "stocks-startup.json"
DIAGNOSTICS = ROOT / "data" / "earnings-refresh-status.json"
LATEST = ROOT / "data" / "earnings-latest.json"
MAX_STARTUP_BYTES = MAX_COLUMNAR_BYTES
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


def candidate_tickers(payload: dict, today: date | None = None, past_days: int = 90, future_days: int = 90, rotation_slot: int = 0) -> list[str]:
    """Reserve bounded slots for companies missing dates.

    Old behaviour only queried symbols that ALREADY had an earnings date,
    so missing upcoming dates could never be discovered. Keep near-term dated
    catalysts, plus large liquid undated equities within the same 80-call cap.
    """
    today = today or date.today()
    start = today - timedelta(days=past_days)
    end = today + timedelta(days=future_days)
    dated = []
    undated = []
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
        if any(d is not None and start <= d <= end for d in dates):
            nearest = min(abs((d - today).days) for d in dates if d is not None and start <= d <= end)
            dated.append((nearest, ticker))
        elif all(d is None or d < today for d in dates):
            # Prefer larger companies; do not randomly scan all listed stocks.
            cap = _number(row.get("market_cap")) or 0
            undated.append((-cap, ticker))
    dated = [ticker for _distance, ticker in sorted(set(dated))]
    # Preserve a small daily watch for large companies whose last published
    # calendar date is stale. Rotating all 30 discovery slots can skip these
    # companies during earnings week even when the source now has a result.
    # This is not evidence of a reported EPS: only provider data can confirm it.
    stale_large_caps = [
        (-(_number(row.get("market_cap")) or 0), str(row.get("ticker") or "").strip().upper())
        for row in payload.get("stocks") or []
        if isinstance(row, dict)
        and str(row.get("quote_type") or "").upper() not in EXCLUDED_TYPES
        and _number(row.get("market_cap")) is not None
        and _number(row.get("market_cap")) >= 50_000_000_000
        and (last := _calendar_date(row.get("analyst_latest_earnings_date"))) is not None
        and last < today - timedelta(days=90)
        and _calendar_date(row.get("analyst_next_earnings_date")) is None
    ]
    pinned = [ticker for _cap, ticker in sorted(set(stale_large_caps))[:10]]
    undated = [ticker for _cap, ticker in sorted(set(undated)) if ticker not in pinned]
    # Move the discovery window daily. A permanently fixed top-30 caused
    # companies ranked below it to remain unqueried forever. A fixed epoch
    # makes selection reproducible in tests and independent of scheduler time.
    if undated:
        rotation_day = (today - date(2026, 10, 12)).days
        # Advance every three UTC hours; multiple refreshes on one day
        # must not exhaust their network budget on the same 30 companies.
        slot = max(0, min(7, int(rotation_slot)))
        offset = ((rotation_day + slot) * 30) % len(undated)
        undated = undated[offset:] + undated[:offset]
    # Preserve the 80-call quota: 50 dated catalysts + up to 10 stale
    # large-cap calendar checks + remaining rotating discovery slots.
    # Never invent a date, estimate or actual EPS.
    dated_set = set(dated[:50])
    pinned = [ticker for ticker in pinned if ticker not in dated_set]
    return dated[:50] + pinned + [
        ticker for ticker in undated if ticker not in dated_set
    ][:30 - len(pinned)]

def overdue_calendar_tickers(packed: dict, today: date | None = None, max_slots: int = 12) -> list[str]:
    """Recheck past events already visible on iPhone even if canonical dates moved.

    The compact startup may retain the last published calendar date while
    stocks-index has moved the next-quarter date forward. This bounded bridge
    only chooses tickers to query: it never assumes that EPS were reported.
    """
    today = today or date.today()
    try:
        rows = unpack_index_payload(packed).get("stocks") or []
    except (TypeError, ValueError, AttributeError):
        return []
    choices = []
    for row in rows:
        if not isinstance(row, dict) or str(row.get("quote_type") or "").upper() in EXCLUDED_TYPES:
            continue
        ticker = str(row.get("ticker") or "").strip().upper()
        if not ticker:
            continue
        dates = [_calendar_date(row.get(key)) for key in ("analyst_next_earnings_date", "analyst_latest_earnings_date")]
        overdue = [d for d in dates if d is not None and 0 <= (today - d).days <= 14]
        if not overdue:
            continue
        cap = _number(row.get("market_cap")) or 0
        choices.append((-cap, min((today - d).days for d in overdue), ticker))
    return list(dict.fromkeys(ticker for _cap, _age, ticker in sorted(choices)))[:max(0, int(max_slots))]


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



def extract_reported_history(ticker: str, earnings_dates, now: datetime | None = None) -> list[dict]:
    """Record all source-confirmed reported quarters, not only the most recent."""
    now = now or datetime.now(timezone.utc)
    events = []
    if earnings_dates is None or getattr(earnings_dates, "empty", True):
        return events
    for idx, row in earnings_dates.iterrows():
        dt = _as_utc_datetime(idx)
        if dt is None or dt > now + timedelta(days=1) or dt < now - timedelta(days=730):
            continue
        actual = _number(_row_value(row, ("Reported EPS", "reportedEPS", "epsActual")))
        if actual is None:
            continue  # Past scheduled dates are not proof of published results.
        estimate = _number(_row_value(row, ("EPS Estimate", "epsEstimate", "epsEstimateCurrent")))
        surprise = _number(_row_value(row, ("Surprise(%)", "surprisePercent", "surprisePct")))
        if surprise is not None:
            surprise /= 100.0
        elif estimate not in (None, 0):
            surprise = actual / estimate - 1.0
        event = {"ticker": ticker, "analyst_latest_earnings_date": dt.date().isoformat(),
                 "analyst_latest_eps_actual": actual, "earnings_source": "yahoo:earnings_dates"}
        if estimate is not None:
            event["analyst_latest_eps_estimate"] = estimate
        if surprise is not None:
            event["analyst_latest_eps_surprise_pct"] = surprise
        events.append(event)
    return events


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
    snapshot = extract_snapshot(earnings_dates, earnings_estimate)
    snapshot['_reported_history'] = extract_reported_history(ticker, earnings_dates)
    if not snapshot.get("analyst_next_earnings_date"):
        # Yahoo's calendar can contain a future Earnings Date even if the
        # earnings-dates/history endpoint has no upcoming rows.
        try:
            calendar = company.get_calendar()
            raw = calendar.get("Earnings Date") if isinstance(calendar, dict) else None
            choices = raw if isinstance(raw, (list, tuple)) else [raw]
            upcoming = sorted(
                d for d in (_calendar_date(v) for v in choices)
                if d is not None and d >= date.today() - timedelta(days=1)
            )
            if upcoming:
                snapshot["analyst_next_earnings_date"] = upcoming[0].isoformat()
        except Exception:
            pass
    return snapshot


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
        values = [_compact_startup_value(row.get(field)) if field in row else None for field in fields]
        while values and values[-1] is None:
            values.pop()
        packed_rows.append(values)
    meta = {key: value for key, value in index_payload.items() if key != "stocks"}
    return {**meta, "layout": "field_rows_v1", "fields": fields, "rows": packed_rows}



def earnings_coverage(payload: dict, today: date | None = None) -> dict[str, int]:
    """Measure confirmed calendar dates, not generic row changes."""
    today = today or date.today()
    window_start = today - timedelta(days=90)
    window_end = today + timedelta(days=90)
    listed = with_dates = past = future = 0
    for row in payload.get("stocks") or []:
        if not isinstance(row, dict):
            continue
        if str(row.get("quote_type") or "").upper() in EXCLUDED_TYPES:
            continue
        if not str(row.get("ticker") or "").strip():
            continue
        listed += 1
        latest = _calendar_date(row.get("analyst_latest_earnings_date"))
        nxt = _calendar_date(row.get("analyst_next_earnings_date"))
        if latest or nxt:
            with_dates += 1
        if latest and window_start <= latest <= today:
            past += 1
        if nxt and today <= nxt <= window_end:
            future += 1
    return {"listed": listed, "companies_with_any_date": with_dates,
            "past_90d_dates": past, "next_90d_dates": future}


def main() -> int:
    payload = json.loads(INDEX.read_text(encoding="utf-8"))
    rows = payload.get("stocks") or []
    by_ticker = {str(row.get("ticker") or "").strip().upper(): row for row in rows if isinstance(row, dict)}
    coverage_before = earnings_coverage(payload)
    now_utc = datetime.now(timezone.utc)
    candidates = candidate_tickers(payload, today=now_utc.date(), rotation_slot=now_utc.hour // 3)
    # Do not silently omit the overdue events still shown by the iPhone
    # calendar when canonical full-universe enrichment moved their dates.
    try:
        calendar_focus = overdue_calendar_tickers(
            json.loads(STARTUP.read_text(encoding="utf-8")), today=now_utc.date()
        )
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        calendar_focus = []
    candidates = list(dict.fromkeys([*calendar_focus, *candidates]))[:80]
    attempted = matched = updated = 0
    failures = []
    discovered_history = []
    history_provider_tickers = set()
    history_rows_by_ticker = {}
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
        reported = snapshot.get('_reported_history') or []
        discovered_history.extend(reported)
        if reported:
            history_provider_tickers.add(ticker)
            history_rows_by_ticker[ticker] = len(reported)
        row = by_ticker.get(ticker)
        if row is not None and apply_snapshot(row, snapshot):
            updated += 1

    packed = pack_index_payload(payload)
    encoded = json.dumps(packed, ensure_ascii=False, separators=(",", ":")) + "\n"
    startup_fits = len(encoded.encode("utf-8")) <= MAX_STARTUP_BYTES
    # Never discard source-confirmed EPS when the dense startup file is near
    # its hard iPhone budget. Publish the independent earnings archive and
    # legacy market index; preserve the previous compact startup unchanged.
    # The calendar loads the archive separately and can reconcile actuals.
    # Do not raise the size budget or truncate individual company records.

    # Publish a bounded earnings-only overlay even when the iPhone startup budget
    # cannot accommodate another stock-index rewrite. The calendar consumes it
    # independently; do not enlarge the general quote/bootstrap payload.
    overlay_rows = []
    period_start = now_utc.date() - timedelta(days=90)
    period_end = now_utc.date() + timedelta(days=90)
    for row in rows:
        if not isinstance(row, dict):
            continue
        ticker = str(row.get("ticker") or "").strip().upper()
        if not ticker or str(row.get("quote_type") or "").strip().upper() in EXCLUDED_TYPES:
            continue
        latest = _calendar_date(row.get("analyst_latest_earnings_date"))
        upcoming = _calendar_date(row.get("analyst_next_earnings_date"))
        if not any(day is not None and period_start <= day <= period_end for day in (latest, upcoming)):
            continue
        entry = {"ticker": ticker, "name": str(row.get("name") or ticker)}
        for field in RESULT_FIELDS:
            value = row.get(field)
            if field.endswith("_date"):
                entry[field] = str(value)[:10] if _calendar_date(value) else None
            else:
                entry[field] = _number(value)
        overlay_rows.append(entry)
    LATEST.write_text(json.dumps({"schema": "vestra_earnings_latest_v1",
        "generated_at": now_utc.isoformat(), "stocks": overlay_rows},
        ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")

    # Persist dated reports before subsequent quarterly refreshes replace latest fields.
    archive = save_archive([*rows, *discovered_history], today=now_utc.date())
    INDEX.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    if startup_fits:
        STARTUP.write_text(encoded, encoding="utf-8")
    status = {
        "state": "checked",
        "startup_updated": startup_fits,
        "latest_overlay_rows": len(overlay_rows),
        "startup_candidate_bytes": len(encoded.encode("utf-8")),
        "startup_budget_bytes": MAX_STARTUP_BYTES,
        "generated_at": now_utc.isoformat(),
        "candidate_count": len(candidates),
        "calendar_overdue_focus": calendar_focus,
        "attempted": attempted,
        "matched": matched,
        "updated": updated,
        "coverage_before": coverage_before,
        "coverage_after": earnings_coverage(payload),
        "archived_events": len(archive["events"]),
        "reported_history_rows": len(discovered_history),
        "reported_history_tickers": len(history_provider_tickers),
        "multi_quarter_source_tickers": sum(count > 1 for count in history_rows_by_ticker.values()),
        "archive_multi_quarter_tickers": sum(count > 1 for count in Counter(event["ticker"] for event in archive["events"]).values()),
        "failures": failures[:10],
        "contract": "near-term earnings only; preserve last verified values on fetch failure",
    }
    DIAGNOSTICS.write_text(json.dumps(status, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps(status, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
