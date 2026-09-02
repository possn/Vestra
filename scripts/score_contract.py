"""Identity-safe boundary around the frozen Vestra scoring engine.

The core score implementation in score.py is intentionally left untouched.
Explicit FUND/MUTUALFUND rows are removed from the cross-sectional equity input
and re-attached as neutral, non-scored rows. If a transient fetch loses the
quote type entirely, exact deterministic identity evidence may recover a known
ETF, or an exact ticker match to a previously published explicit fund may carry
that fund identity forward. Conflicting explicit current types always win;
missing/unknown identities without evidence remain in the legacy candidate path.
"""
from __future__ import annotations

import json
from pathlib import Path

from asset_types import is_fund_type, is_explicit_non_equity, normalized_quote_type
from known_asset_identity import exact_identity_override

ROOT = Path(__file__).resolve().parents[1]
STOCKS_SNAPSHOT = ROOT / "data" / "stocks.json"


def _load_core():
    """Load the frozen score engine only when scoring actually runs.

    Architecture CI deliberately avoids installing heavy market dependencies
    such as yfinance. The production pipeline installs them before importing the
    score engine, so a lazy boundary keeps unit tests lightweight without
    changing runtime behaviour.
    """
    from score import ScoredTicker, score_universe as core_score_universe
    return ScoredTicker, core_score_universe


def _previous_funds(path=STOCKS_SNAPSHOT):
    """Return exact-ticker prior FUND/MUTUALFUND rows from the last publication.

    The snapshot is identity evidence only when it already carries an explicit
    fund type. No name matching, ticker normalization beyond trim/uppercase, or
    inference from missing data is permitted.
    """
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        rows = payload.get("stocks") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            return {}
        out = {}
        for row in rows:
            if not isinstance(row, dict) or not is_fund_type(row.get("quote_type")):
                continue
            ticker = str(row.get("ticker") or "").strip().upper()
            if ticker:
                out[ticker] = row
        return out
    except Exception:
        return {}


def _value(current, previous, key, default=None):
    value = getattr(current, key, None)
    if value is not None:
        return value
    if isinstance(previous, dict):
        value = previous.get(key)
        if value is not None:
            return value
    return default


def _neutral_asset(r, scored_cls, previous=None, quote_type=None):
    return scored_cls(
        ticker=r.ticker,
        name=_value(r, previous, "name", r.ticker),
        business_summary=_value(r, previous, "business_summary"),
        sector=_value(r, previous, "sector"),
        industry=_value(r, previous, "industry"),
        market_cap=_value(r, previous, "market_cap"),
        currency=_value(r, previous, "currency"),
        quote_type=normalized_quote_type(quote_type or getattr(r, "quote_type", None) or (previous or {}).get("quote_type")),
        score=None,
        data_confidence="low",
        data_coverage_pct=0,
        zombie="unknown",
        interest_coverage=None,
        profitability_pct=None,
        leverage_pct=None,
        value_pct=None,
        stability_pct=None,
        quality_pct=None,
        growth_pct=None,
        balance_pct=None,
        cashflow_pct=None,
        expense_ratio=_value(r, previous, "expense_ratio"),
        current_price=_value(r, previous, "current_price"),
    )


def _apply_exact_override(r, override):
    """Apply only identity fields when the current provider supplied no type."""
    if not isinstance(override, dict):
        return
    ticker = str(getattr(r, "ticker", "") or "").strip().upper()
    current_name = str(getattr(r, "name", "") or "").strip()
    setattr(r, "quote_type", normalized_quote_type(override.get("quote_type")))
    if override.get("name") and (not current_name or current_name.upper() == ticker):
        setattr(r, "name", override["name"])
    if override.get("isin"):
        setattr(r, "isin", override["isin"])
    if override.get("identity_source"):
        setattr(r, "identity_source", override["identity_source"])


def score_universe(raw, previous_path=STOCKS_SNAPSHOT):
    """Delegate score math unchanged after identity-safe non-equity isolation."""
    scored_cls, core_score_universe = _load_core()
    previous_funds = _previous_funds(previous_path)
    neutral_rows = []
    score_input = []

    for r in raw:
        ticker = str(getattr(r, "ticker", "") or "").strip().upper()
        current_type = normalized_quote_type(getattr(r, "quote_type", None))
        previous = previous_funds.get(ticker)
        override = exact_identity_override(ticker)

        # Deterministic overrides are allowed only when the live provider lost
        # the type entirely. Explicit current identity always wins.
        if not current_type and override is not None:
            _apply_exact_override(r, override)
            current_type = normalized_quote_type(getattr(r, "quote_type", None))
            if current_type == "ETF" and getattr(r, "error", None) is not None:
                neutral_rows.append((r, override, current_type))
                continue

        if is_fund_type(current_type):
            neutral_rows.append((r, previous, current_type))
            continue

        # Carry forward fund identity only when the current provider lost the
        # type entirely. An explicit EQUITY/ETF/CRYPTO/other current type is a
        # conflict and must never be overwritten by stale snapshot evidence.
        if not current_type and previous is not None:
            neutral_rows.append((r, previous, previous.get("quote_type")))
            continue

        # If a known override ETF is explicitly typed as ETF but the rest of the
        # fetch failed, preserve its identity instead of letting core drop it.
        if current_type == "ETF" and getattr(r, "error", None) is not None and override is not None:
            neutral_rows.append((r, override, current_type))
            continue

        score_input.append(r)

    scored = list(core_score_universe(score_input))
    scored.extend(_neutral_asset(r, scored_cls, previous, quote_type) for r, previous, quote_type in neutral_rows)
    return scored


__all__ = ["score_universe", "is_explicit_non_equity"]
