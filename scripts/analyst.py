"""Analyst / earnings expectation intelligence from yfinance.

This module deliberately keeps analyst data OUT of the core Finscanner score.
Coverage is inconsistent across markets and Yahoo can temporarily omit whole
analysis modules. The output is therefore contextual evidence: estimates,
revisions, surprise history and price-target consensus.

The API surface used here is documented by yfinance's public Ticker analysis
methods (earnings_estimate, revenue_estimate, eps_trend, eps_revisions,
earnings_history, recommendations and analyst_price_targets).
"""
from __future__ import annotations

import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yfinance as yf

log = logging.getLogger("analyst")


def _float(v):
    if v is None:
        return None
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    if x != x or x in (float("inf"), float("-inf")):
        return None
    return x


def _int(v):
    x = _float(v)
    return int(x) if x is not None else None


def _df_cell(df, idx: str, col: str):
    if df is None or getattr(df, "empty", True):
        return None
    try:
        if idx in df.index and col in df.columns:
            return df.loc[idx, col]
    except Exception:
        return None
    return None


def _safe_call(fn):
    try:
        return fn()
    except Exception:
        return None


def _parse_time(value):
    text = str(value or "").strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _snapshot_age_days(snapshot: dict[str, Any] | None, now: datetime | None = None):
    if not snapshot:
        return None
    dt = _parse_time(snapshot.get("fetched_at"))
    if dt is None:
        return None
    now = now or datetime.now(timezone.utc)
    return max(0.0, (now - dt).total_seconds() / 86400.0)


def _cacheable(snapshot: dict[str, Any] | None, max_age_days: float, now: datetime | None = None) -> bool:
    if not snapshot or _float(snapshot.get("coverage_pct")) in (None, 0):
        return False
    age = _snapshot_age_days(snapshot, now=now)
    return age is not None and age <= max_age_days


def _load_previous_snapshots(path: str | os.PathLike | None = None) -> dict[str, dict[str, Any]]:
    """Read analyst-prefixed fields from the last validated market payload.

    The cache is deliberately sourced only from the canonical published file,
    never from a side cache. This means a coverage-gate rejection cannot promote
    unvalidated analyst data into the next run.
    """
    source = Path(path) if path is not None else Path(__file__).resolve().parents[1] / "data" / "stocks.json"
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except Exception:
        return {}
    generated_at = payload.get("generated_at") or payload.get("as_of") or payload.get("updated_at")
    out: dict[str, dict[str, Any]] = {}
    for row in payload.get("stocks") or []:
        if not isinstance(row, dict):
            continue
        ticker = str(row.get("ticker") or "").strip().upper()
        if not ticker:
            continue
        snap = {
            key[len("analyst_"):]: value
            for key, value in row.items()
            if str(key).startswith("analyst_")
        }
        if not snap or snap.get("status") == "not_requested" or _float(snap.get("coverage_pct")) in (None, 0):
            continue
        snap["ticker"] = ticker
        if not snap.get("fetched_at") and generated_at:
            snap["fetched_at"] = str(generated_at)
        out[ticker] = snap
    return out


@dataclass
class AnalystSnapshot:
    ticker: str
    status: str = "not_available"
    coverage_pct: float = 0.0
    fetched_at: str | None = None
    refresh_state: str = "fresh"
    snapshot_age_days: float | None = 0.0

    # Forward estimates
    eps_next_q: float | None = None
    eps_next_q_low: float | None = None
    eps_next_q_high: float | None = None
    eps_next_q_analysts: int | None = None
    eps_next_q_growth: float | None = None
    eps_next_y: float | None = None
    eps_next_y_growth: float | None = None
    eps_next_y_analysts: int | None = None

    revenue_next_q: float | None = None
    revenue_next_q_low: float | None = None
    revenue_next_q_high: float | None = None
    revenue_next_q_analysts: int | None = None
    revenue_next_q_growth: float | None = None
    revenue_next_y: float | None = None
    revenue_next_y_growth: float | None = None
    revenue_next_y_analysts: int | None = None

    # Estimate momentum / revisions
    eps_next_q_30d_ago: float | None = None
    eps_next_q_revision_30d_pct: float | None = None
    eps_next_y_30d_ago: float | None = None
    eps_next_y_revision_30d_pct: float | None = None
    eps_revisions_up_30d: int | None = None
    eps_revisions_down_30d: int | None = None

    # Earnings calendar / catalyst window
    next_earnings_date: str | None = None
    days_to_earnings: int | None = None
    catalyst_window: str | None = None
    earnings_history_4q: list[dict[str, Any]] | None = None
    earnings_beats_4q: int | None = None
    earnings_misses_4q: int | None = None
    earnings_avg_surprise_4q: float | None = None
    earnings_beat_streak: int | None = None

    # Latest reported earnings surprise
    latest_earnings_date: str | None = None
    latest_eps_estimate: float | None = None
    latest_eps_actual: float | None = None
    latest_eps_surprise_pct: float | None = None

    # Consensus recommendations
    strong_buy: int | None = None
    buy: int | None = None
    hold: int | None = None
    sell: int | None = None
    strong_sell: int | None = None

    # Analyst price targets
    price_target_current: float | None = None
    price_target_low: float | None = None
    price_target_high: float | None = None
    price_target_mean: float | None = None
    price_target_median: float | None = None
    price_target_upside_pct: float | None = None

    error: str | None = None


def fetch_one(ticker: str, current_price: float | None = None) -> AnalystSnapshot:
    out = AnalystSnapshot(ticker=ticker, fetched_at=datetime.now(timezone.utc).isoformat())
    try:
        t = yf.Ticker(ticker)

        earnings_est = _safe_call(t.get_earnings_estimate)
        revenue_est = _safe_call(t.get_revenue_estimate)
        eps_trend = _safe_call(t.get_eps_trend)
        eps_revisions = _safe_call(t.get_eps_revisions)
        earnings_history = _safe_call(t.get_earnings_history)
        earnings_dates = _safe_call(lambda: t.get_earnings_dates(limit=12))
        recommendations = _safe_call(t.get_recommendations)
        targets = _safe_call(t.get_analyst_price_targets)

        # Forward EPS
        out.eps_next_q = _float(_df_cell(earnings_est, "+1q", "avg"))
        out.eps_next_q_low = _float(_df_cell(earnings_est, "+1q", "low"))
        out.eps_next_q_high = _float(_df_cell(earnings_est, "+1q", "high"))
        out.eps_next_q_analysts = _int(_df_cell(earnings_est, "+1q", "numberOfAnalysts"))
        out.eps_next_q_growth = _float(_df_cell(earnings_est, "+1q", "growth"))
        out.eps_next_y = _float(_df_cell(earnings_est, "+1y", "avg"))
        out.eps_next_y_growth = _float(_df_cell(earnings_est, "+1y", "growth"))
        out.eps_next_y_analysts = _int(_df_cell(earnings_est, "+1y", "numberOfAnalysts"))

        # Forward revenue
        out.revenue_next_q = _float(_df_cell(revenue_est, "+1q", "avg"))
        out.revenue_next_q_low = _float(_df_cell(revenue_est, "+1q", "low"))
        out.revenue_next_q_high = _float(_df_cell(revenue_est, "+1q", "high"))
        out.revenue_next_q_analysts = _int(_df_cell(revenue_est, "+1q", "numberOfAnalysts"))
        out.revenue_next_q_growth = _float(_df_cell(revenue_est, "+1q", "growth"))
        out.revenue_next_y = _float(_df_cell(revenue_est, "+1y", "avg"))
        out.revenue_next_y_growth = _float(_df_cell(revenue_est, "+1y", "growth"))
        out.revenue_next_y_analysts = _int(_df_cell(revenue_est, "+1y", "numberOfAnalysts"))

        # Revisions: compare the current consensus with 30d ago. This is not a
        # realized earnings change; it is a change in analyst expectations.
        q_cur = _float(_df_cell(eps_trend, "+1q", "current"))
        q_30 = _float(_df_cell(eps_trend, "+1q", "30daysAgo"))
        out.eps_next_q_30d_ago = q_30
        if q_cur is not None and q_30 not in (None, 0):
            out.eps_next_q_revision_30d_pct = q_cur / q_30 - 1.0
        y_cur = _float(_df_cell(eps_trend, "+1y", "current"))
        y_30 = _float(_df_cell(eps_trend, "+1y", "30daysAgo"))
        out.eps_next_y_30d_ago = y_30
        if y_cur is not None and y_30 not in (None, 0):
            out.eps_next_y_revision_30d_pct = y_cur / y_30 - 1.0
        out.eps_revisions_up_30d = _int(_df_cell(eps_revisions, "+1q", "upLast30days"))
        out.eps_revisions_down_30d = _int(_df_cell(eps_revisions, "+1q", "downLast30days"))

        # Upcoming earnings date. get_earnings_dates normally includes future
        # and recent reported rows. Parse defensively because Yahoo column
        # labels and timezone metadata have varied across versions.
        if earnings_dates is not None and not getattr(earnings_dates, "empty", True):
            try:
                now = datetime.now(timezone.utc)
                future = []
                for idx, row in earnings_dates.iterrows():
                    try:
                        dt = idx.to_pydatetime() if hasattr(idx, "to_pydatetime") else idx
                        if getattr(dt, "tzinfo", None) is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        else:
                            dt = dt.astimezone(timezone.utc)
                        reported = None
                        for c in ("Reported EPS", "reportedEPS", "epsActual"):
                            try:
                                if c in row.index:
                                    reported = _float(row.get(c))
                                    break
                            except Exception:
                                pass
                        if dt >= now and reported is None:
                            future.append((dt, row))
                    except Exception:
                        continue
                if future:
                    dt, _row = sorted(future, key=lambda x: x[0])[0]
                    out.next_earnings_date = dt.date().isoformat()
                    out.days_to_earnings = max(0, (dt.date() - now.date()).days)
                    d = out.days_to_earnings
                    out.catalyst_window = "imminent" if d <= 3 else "this_week" if d <= 7 else "near" if d <= 14 else "scheduled"
            except Exception:
                pass

        # Latest earnings surprise + compact four-quarter surprise history.
        if earnings_history is not None and not getattr(earnings_history, "empty", True):
            try:
                hist = earnings_history.sort_index(ascending=False)
                row = hist.iloc[0]
                idx = hist.index[0]
                out.latest_earnings_date = getattr(idx, "date", lambda: idx)().isoformat() if hasattr(getattr(idx, "date", None), "__call__") else str(idx)
                out.latest_eps_estimate = _float(row.get("epsEstimate"))
                out.latest_eps_actual = _float(row.get("epsActual"))
                out.latest_eps_surprise_pct = _float(row.get("surprisePercent"))
                if out.latest_eps_surprise_pct is not None and abs(out.latest_eps_surprise_pct) > 2:
                    out.latest_eps_surprise_pct /= 100.0

                q4 = []
                beats = misses = 0
                surprises = []
                streak = 0
                for hidx, hrow in hist.head(4).iterrows():
                    surprise = _float(hrow.get("surprisePercent"))
                    if surprise is not None and abs(surprise) > 2:
                        surprise /= 100.0
                    actual = _float(hrow.get("epsActual"))
                    estimate = _float(hrow.get("epsEstimate"))
                    if surprise is None and actual is not None and estimate not in (None, 0):
                        surprise = actual / estimate - 1.0
                    if surprise is not None:
                        surprises.append(surprise)
                        if surprise > 0:
                            beats += 1
                        elif surprise < 0:
                            misses += 1
                    try:
                        hdate = hidx.date().isoformat()
                    except Exception:
                        hdate = str(hidx)[:10]
                    q4.append({"date": hdate, "estimate": estimate, "actual": actual, "surprise_pct": surprise})
                for q in q4:
                    sp = q.get("surprise_pct")
                    if sp is not None and sp > 0:
                        streak += 1
                    else:
                        break
                out.earnings_history_4q = q4
                out.earnings_beats_4q = beats
                out.earnings_misses_4q = misses
                out.earnings_avg_surprise_4q = (sum(surprises) / len(surprises)) if surprises else None
                out.earnings_beat_streak = streak
            except Exception:
                pass

        if recommendations is not None and not getattr(recommendations, "empty", True):
            try:
                rr = recommendations.iloc[0]
                out.strong_buy = _int(rr.get("strongBuy"))
                out.buy = _int(rr.get("buy"))
                out.hold = _int(rr.get("hold"))
                out.sell = _int(rr.get("sell"))
                out.strong_sell = _int(rr.get("strongSell"))
            except Exception:
                pass

        if isinstance(targets, dict):
            out.price_target_current = _float(targets.get("current"))
            out.price_target_low = _float(targets.get("low"))
            out.price_target_high = _float(targets.get("high"))
            out.price_target_mean = _float(targets.get("mean"))
            out.price_target_median = _float(targets.get("median"))
            base = current_price if current_price not in (None, 0) else out.price_target_current
            if base not in (None, 0) and out.price_target_mean is not None:
                out.price_target_upside_pct = out.price_target_mean / base - 1.0

        blocks = [
            out.eps_next_q is not None or out.eps_next_y is not None,
            out.revenue_next_q is not None or out.revenue_next_y is not None,
            out.eps_next_q_revision_30d_pct is not None or out.eps_revisions_up_30d is not None,
            out.latest_eps_actual is not None or out.latest_eps_surprise_pct is not None or out.next_earnings_date is not None,
            any(v is not None for v in (out.strong_buy, out.buy, out.hold, out.sell, out.strong_sell)),
            out.price_target_mean is not None,
        ]
        out.coverage_pct = round(sum(blocks) / len(blocks) * 100.0, 1)
        if out.coverage_pct >= 50:
            out.status = "ok"
        elif out.coverage_pct > 0:
            out.status = "partial"
        else:
            out.status = "not_available"
    except Exception as exc:
        out.status = "error"
        out.error = f"{type(exc).__name__}: {exc}"[:240]
    return out


def _cached_copy(snapshot: dict[str, Any], state: str, now: datetime) -> dict[str, Any]:
    cached = dict(snapshot)
    cached["refresh_state"] = state
    age = _snapshot_age_days(cached, now=now)
    cached["snapshot_age_days"] = round(age, 2) if age is not None else None
    return cached


def fetch_many(rows: list[dict], priority_tickers: set[str] | None = None) -> dict[str, dict[str, Any]]:
    """Refresh priority analyst evidence and rotate the rest of the universe.

    Portfolio/priority names are refreshed on every run. Non-priority names are
    refreshed from a bounded rotating budget ordered by missing/stale snapshots
    and then by score/market cap. Recent validated snapshots are carried forward
    for a short TTL so reducing Yahoo request pressure does not make dossiers
    oscillate between rich data and ``not_requested``. Cached analyst evidence is
    contextual only and never enters the core score.
    """
    priority_tickers = set(priority_tickers or set())
    equities = [r for r in rows if r.get("quote_type") != "ETF" and r.get("ticker")]
    max_rows = max(50, int(os.getenv("FINSCANNER_ANALYST_MAX", "800")))
    nonpriority_budget = max(0, int(os.getenv("FINSCANNER_ANALYST_NONPRIORITY_REFRESH", "220")))
    max_cache_age = max(1.0, float(os.getenv("FINSCANNER_ANALYST_CACHE_MAX_AGE_DAYS", "14")))
    now = datetime.now(timezone.utc)
    previous = _load_previous_snapshots()

    priority = [r for r in equities if r.get("ticker") in priority_tickers]
    other = [r for r in equities if r.get("ticker") not in priority_tickers]

    def rotation_key(row):
        ticker = row.get("ticker")
        prev = previous.get(ticker)
        age = _snapshot_age_days(prev, now=now)
        missing_or_expired = not _cacheable(prev, max_cache_age, now=now)
        stale_age = age if age is not None else max_cache_age + 1000.0
        return (
            1 if missing_or_expired else 0,
            stale_age,
            float(row.get("score") or 0),
            float(row.get("market_cap") or 0),
            str(ticker),
        )

    other.sort(key=rotation_key, reverse=True)
    available_slots = max(0, max_rows - len(priority))
    refresh_slots = min(nonpriority_budget, available_slots)
    targets = priority + other[:refresh_slots]

    dedup = {}
    for r in targets:
        dedup[r.get("ticker")] = r
    targets = [r for r in dedup.values() if r.get("ticker")]
    target_tickers = {r["ticker"] for r in targets}

    workers = max(1, min(12, int(os.getenv("FINSCANNER_ANALYST_WORKERS", "8"))))
    log.info(
        "Analyst intelligence: refreshing %d/%d equities (%d priority, %d rotating), workers=%d; previous usable snapshots=%d",
        len(targets), len(equities), len(priority), max(0, len(targets) - len(priority)), workers,
        sum(_cacheable(v, max_cache_age, now=now) for v in previous.values()),
    )

    out: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(fetch_one, r["ticker"], _float(r.get("current_price"))): r["ticker"] for r in targets}
        done = 0
        for fut in as_completed(futs):
            ticker = futs[fut]
            try:
                snap = fut.result()
            except Exception as exc:
                snap = AnalystSnapshot(
                    ticker=ticker,
                    status="error",
                    fetched_at=now.isoformat(),
                    error=f"{type(exc).__name__}: {exc}"[:240],
                )
            fresh = asdict(snap)
            prev = previous.get(ticker)
            if _float(fresh.get("coverage_pct")) in (None, 0) and _cacheable(prev, max_cache_age, now=now):
                out[ticker] = _cached_copy(prev, "cached_after_refresh_failure", now)
            else:
                fresh["refresh_state"] = "fresh"
                fresh["snapshot_age_days"] = 0.0
                out[ticker] = fresh
            done += 1
            if done % 100 == 0 or done == len(targets):
                log.info("Analyst intelligence progress: %d/%d", done, len(targets))

    carried = 0
    for row in equities:
        ticker = row.get("ticker")
        if not ticker or ticker in target_tickers or ticker in out:
            continue
        prev = previous.get(ticker)
        if _cacheable(prev, max_cache_age, now=now):
            out[ticker] = _cached_copy(prev, "cached_rotation", now)
            carried += 1

    if carried:
        log.info("Analyst intelligence: carried %d recent validated snapshots without Yahoo refresh", carried)
    return out
