"""Rolling history of explainable investment-thesis snapshots.

The file is intentionally compact and deterministic.  It stores only the fields
needed to answer a future question: "is the thesis strengthening, stable or
weakening?"  It is not a price-return backtest and must not be treated as one.
"""
from __future__ import annotations

import json
import logging
import os

log = logging.getLogger("thesis_history")
MAX_DAYS = 365

SNAPSHOT_FIELDS = (
    "thesis_type", "thesis_slug", "thesis_confidence", "score",
    "quality_pct", "growth_pct", "balance_pct", "cashflow_pct", "value_pct",
    "stability_pct", "revenue_yoy_latest", "revenue_yoy_prior",
    "revenue_yoy_acceleration_pp", "net_income_yoy_latest",
    "net_income_yoy_prior", "net_income_yoy_acceleration_pp",
    "net_margin_yoy_change_pp", "net_margin_yoy_change_prior_pp",
    "diluted_shares_yoy", "insider_net_value_30d", "zombie",
    "analyst_eps_next_y_revision_30d_pct", "analyst_eps_next_q_revision_30d_pct",
    "analyst_price_target_upside_pct", "analyst_latest_earnings_date",
    "analyst_latest_eps_surprise_pct", "analyst_days_to_earnings",
)


def load(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            obj = json.load(f)
        return obj if isinstance(obj, dict) else {}
    except Exception as exc:
        log.warning("Could not load thesis history at %s (%s) — starting fresh", path, exc)
        return {}


def snapshot(row: dict) -> dict:
    return {k: row.get(k) for k in SNAPSHOT_FIELDS if row.get(k) is not None}


def previous(history: dict, ticker: str, before_date: str | None = None) -> tuple[str | None, dict | None]:
    series = history.get(ticker) or {}
    if not isinstance(series, dict) or not series:
        return None, None
    dates = sorted(d for d in series if before_date is None or d < before_date)
    if not dates:
        return None, None
    d = dates[-1]
    v = series.get(d)
    return d, v if isinstance(v, dict) else None


def nearest_days_ago(history: dict, ticker: str, today: str, days: int = 30) -> tuple[str | None, dict | None]:
    """Return the latest observation at least `days` calendar days before today.
    Falls back to the oldest available observation if history exists but is younger.
    """
    import datetime as dt
    try:
        cutoff = (dt.date.fromisoformat(today) - dt.timedelta(days=days)).isoformat()
    except Exception:
        return None, None
    series = history.get(ticker) or {}
    dates = sorted(series)
    eligible = [d for d in dates if d <= cutoff]
    if eligible:
        d = eligible[-1]
        return d, series[d]
    if dates:
        d = dates[0]
        return d, series[d]
    return None, None


def update(history: dict, rows: list[dict], today: str) -> dict:
    for row in rows:
        ticker = row.get("ticker")
        if not ticker:
            continue
        series = history.setdefault(ticker, {})
        series[today] = snapshot(row)
        if len(series) > MAX_DAYS:
            for old in sorted(series)[: len(series) - MAX_DAYS]:
                del series[old]
    return history


def save(history: dict, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(history, f, separators=(",", ":"))
    log.info("Wrote thesis history for %d tickers to %s", len(history), path)
