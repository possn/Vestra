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

import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
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


@dataclass
class AnalystSnapshot:
    ticker: str
    status: str = "not_available"
    coverage_pct: float = 0.0

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
    out = AnalystSnapshot(ticker=ticker)
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
                        # Rows with reported EPS populated are already past even
                        # if Yahoo provides a slightly future-normalized timestamp.
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

        # Recommendation trend: first row is the most recent period in Yahoo's
        # current response (typically 0m).
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

        # Coverage is based on six independent evidence blocks, not individual
        # scalar fields, so one rich module cannot mask five missing modules.
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


def fetch_many(rows: list[dict], priority_tickers: set[str] | None = None) -> dict[str, dict[str, Any]]:
    """Fetch analyst evidence for a bounded, useful subset of equities.

    The universe can exceed ~1,500 equities. Analyst endpoints are materially
    heavier than basic price/fundamental fetches, so we guarantee portfolio/
    priority names first and then fill the remaining budget with larger/high-
    score companies. This prevents a daily static-site workflow from turning
    into an unbounded Yahoo crawl.
    """
    priority_tickers = set(priority_tickers or set())
    equities = [r for r in rows if r.get("quote_type") != "ETF"]
    max_rows = max(50, int(os.getenv("FINSCANNER_ANALYST_MAX", "800")))

    priority = [r for r in equities if r.get("ticker") in priority_tickers]
    other = [r for r in equities if r.get("ticker") not in priority_tickers]
    other.sort(key=lambda r: (float(r.get("score") or 0), float(r.get("market_cap") or 0)), reverse=True)
    targets = priority + other[: max(0, max_rows - len(priority))]
    # preserve one row per ticker
    dedup = {}
    for r in targets:
        dedup[r.get("ticker")] = r
    targets = [r for r in dedup.values() if r.get("ticker")]

    workers = max(1, min(12, int(os.getenv("FINSCANNER_ANALYST_WORKERS", "8"))))
    log.info("Analyst intelligence: %d/%d equities requested (%d priority), workers=%d", len(targets), len(equities), len(priority), workers)
    out: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(fetch_one, r["ticker"], _float(r.get("current_price"))): r["ticker"] for r in targets}
        done = 0
        for fut in as_completed(futs):
            ticker = futs[fut]
            try:
                snap = fut.result()
            except Exception as exc:
                snap = AnalystSnapshot(ticker=ticker, status="error", error=f"{type(exc).__name__}: {exc}"[:240])
            out[ticker] = asdict(snap)
            done += 1
            if done % 100 == 0 or done == len(targets):
                log.info("Analyst intelligence progress: %d/%d", done, len(targets))
    return out
