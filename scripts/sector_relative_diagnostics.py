"""Read-only reasons why point-in-time sector comparisons are unavailable."""
from collections import Counter

from sector_relative_context import SECTOR_ETF, evidence


def exclusion_summary(scored, prices):
    reasons = Counter()
    for item in scored:
        ticker = getattr(item, "ticker", None)
        sector = getattr(item, "sector", None)
        quote_type = getattr(item, "quote_type", None)
        if quote_type == "ETF" or not ticker or "." in ticker or sector not in SECTOR_ETF:
            continue
        etf = SECTOR_ETF[sector]
        if evidence(ticker, sector, prices):
            reasons["verified"] += 1
            continue
        stock = prices.get(ticker) or {}
        peer = prices.get(etf) or {}
        if not stock.get("market_return_20d_dates"):
            reasons["stock_sessions_missing"] += 1
        elif not peer.get("market_return_20d_dates"):
            reasons["etf_sessions_missing"] += 1
        elif stock.get("market_return_asof_date") != peer.get("market_return_asof_date"):
            reasons["latest_session_mismatch"] += 1
        elif stock["market_return_20d_dates"] != peer["market_return_20d_dates"]:
            reasons["session_calendar_mismatch"] += 1
        else:
            reasons["other_invalid_evidence"] += 1
    return {"total": sum(reasons.values()), "reasons": dict(sorted(reasons.items()))}
