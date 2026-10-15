"""Point-in-time aligned US sector ETF comparison, never ranking alpha."""
import math

SECTOR_ETF = {
    "Technology":"XLK", "Financial Services":"XLF", "Energy":"XLE",
    "Healthcare":"XLV", "Industrials":"XLI", "Consumer Cyclical":"XLY",
    "Consumer Defensive":"XLP", "Utilities":"XLU",
    "Basic Materials":"XLB", "Real Estate":"XLRE", "Communication Services":"XLC",
}

def evidence(ticker, sector, prices):
    blank={}
    if not ticker or "." in ticker or not isinstance(sector,str):
        return blank
    etf=SECTOR_ETF.get(sector)
    if not etf:
        return blank
    stock=prices.get(ticker) or {}
    peer=prices.get(etf) or {}
    try:
        stock_return=float(stock["market_return_20d_pct"])
        sector_return=float(peer["market_return_20d_pct"])
        stock_date=str(stock["market_return_asof_date"])
        peer_date=str(peer["market_return_asof_date"])
        dates=stock["market_return_20d_dates"]
        peer_dates=peer["market_return_20d_dates"]
        if (not all(math.isfinite(x) for x in (stock_return,sector_return))
                or len(stock_date)!=10 or stock_date!=peer_date
                or not isinstance(dates,list) or len(dates)!=21 or dates!=peer_dates):
            return blank
    except (ValueError,TypeError,KeyError):
        return blank
    return {
        "opportunity_stock_return_20d_pct":stock_return,
        "opportunity_sector_return_20d_pct":sector_return,
        "opportunity_sector_benchmark_ticker":etf,
        "opportunity_sector_benchmark_asof_date":peer_date,
        "opportunity_sector_benchmark_verified":True,
    }
