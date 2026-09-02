"""Identity-safe boundary around the frozen Vestra scoring engine.

The core score implementation in score.py is intentionally left untouched.
Only rows already carrying an explicit FUND/MUTUALFUND quote type are removed
from the cross-sectional equity input, then re-attached as neutral, non-scored
rows. Missing/unknown quote types remain in the legacy equity-candidate path.
"""
from __future__ import annotations

from asset_types import is_fund_type, is_explicit_non_equity, normalized_quote_type


def _load_core():
    """Load the frozen score engine only when scoring actually runs.

    Architecture CI deliberately avoids installing heavy market dependencies
    such as yfinance. The production pipeline installs them before importing the
    score engine, so a lazy boundary keeps unit tests lightweight without
    changing runtime behaviour.
    """
    from score import ScoredTicker, score_universe as core_score_universe
    return ScoredTicker, core_score_universe


def _neutral_fund(r, scored_cls):
    return scored_cls(
        ticker=r.ticker,
        name=r.name,
        business_summary=getattr(r, "business_summary", None),
        sector=r.sector,
        industry=r.industry,
        market_cap=r.market_cap,
        currency=r.currency,
        quote_type=normalized_quote_type(r.quote_type),
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
        expense_ratio=getattr(r, "expense_ratio", None),
        current_price=getattr(r, "current_price", None),
    )


def score_universe(raw):
    """Delegate all score math unchanged after removing explicit fund rows."""
    scored_cls, core_score_universe = _load_core()
    funds = [r for r in raw if is_fund_type(getattr(r, "quote_type", None)) and getattr(r, "error", None) is None]
    score_input = [r for r in raw if not is_fund_type(getattr(r, "quote_type", None))]
    scored = list(core_score_universe(score_input))
    scored.extend(_neutral_fund(r, scored_cls) for r in funds)
    return scored


__all__ = ["score_universe", "is_explicit_non_equity"]
