"""
score.py — explainable multi-factor investment scoring engine.

The score is cross-sectional: each metric is ranked against the currently
fetched equity universe. It is a screening model, not a return forecast.
Missing data are excluded rather than treated as zero.

General-company dimensions / weights (v3):
  Quality          18%  ROE, ROA, net/operating/gross margins
  Growth           15%  revenue and earnings growth
  Balance          14%  liquidity, leverage, net cash, interest coverage
  Cash flow         8%  FCF yield and positive operating cash flow
  Valuation        12%  trailing/forward P-E, P/B, EV/EBITDA, PEG
  Execution        10%  revenue/margin/EPS momentum
  Earnings quality 10%  cash conversion, accrual discipline, FCF margin
  Capital alloc.    8%  dilution/buybacks, ROCE, dividend FCF coverage
  Stability         5%  beta (lower is better)

A data confidence score is also emitted, based on metric coverage.
"""
from __future__ import annotations

from dataclasses import dataclass

from fundamentals import RawMetrics


@dataclass
class ScoredTicker:
    ticker: str
    name: str | None
    sector: str | None
    industry: str | None
    market_cap: float | None
    currency: str | None
    quote_type: str | None

    score: float | None
    data_confidence: str
    data_coverage_pct: float

    zombie: str
    interest_coverage: float | None

    # dimension scores
    profitability_pct: float | None  # retained for backward-compatible UI
    leverage_pct: float | None       # retained for backward-compatible UI
    value_pct: float | None
    stability_pct: float | None
    quality_pct: float | None
    growth_pct: float | None
    balance_pct: float | None
    cashflow_pct: float | None
    execution_pct: float | None = None
    earnings_quality_pct: float | None = None
    capital_allocation_pct: float | None = None

    # raw metrics for the company dossier
    roe: float | None = None
    roa: float | None = None
    profit_margin: float | None = None
    operating_margin: float | None = None
    gross_margin: float | None = None
    revenue_growth: float | None = None
    earnings_growth: float | None = None
    earnings_quarterly_growth: float | None = None
    free_cash_flow: float | None = None
    operating_cash_flow: float | None = None
    fcf_yield: float | None = None
    current_ratio: float | None = None
    quick_ratio: float | None = None
    debt_to_equity: float | None = None
    net_cash: float | None = None
    trailing_pe: float | None = None
    forward_pe: float | None = None
    price_to_book: float | None = None
    enterprise_to_ebitda: float | None = None
    peg_ratio: float | None = None
    dividend_yield: float | None = None
    payout_ratio: float | None = None
    beta: float | None = None

    # quality-of-earnings / capital-allocation diagnostics
    cash_conversion_ratio: float | None = None
    accrual_ratio: float | None = None
    fcf_margin: float | None = None
    ttm_net_income: float | None = None
    ttm_revenue: float | None = None
    diluted_shares_yoy: float | None = None
    repurchases_last_quarter: float | None = None
    dividend_fcf_coverage: float | None = None
    roce_proxy: float | None = None

    expense_ratio: float | None = None
    ai_exposure_pct: float | None = None
    current_price: float | None = None
    business_summary: str | None = None

    # peer-relative valuation context
    peer_count: int | None = None
    sector_trailing_pe_median: float | None = None
    trailing_pe_vs_sector_pct: float | None = None
    sector_forward_pe_median: float | None = None
    forward_pe_vs_sector_pct: float | None = None
    sector_pb_median: float | None = None
    pb_vs_sector_pct: float | None = None
    sector_ev_ebitda_median: float | None = None
    ev_ebitda_vs_sector_pct: float | None = None
    quality_value_score: float | None = None
    sector_roe_median: float | None = None
    sector_operating_margin_median: float | None = None
    sector_gross_margin_median: float | None = None
    sector_roce_proxy_median: float | None = None
    sector_dividend_yield_median: float | None = None
    sector_fcf_yield_median: float | None = None
    score_model: str = "general"
    score_model_note: str | None = None
    score_dimensions: dict[str, float | None] | None = None
    risk_flags: list[str] | None = None
    risk_gate: str = "clear"
    score_cap: float | None = None

    # bank-native statement-derived proxies
    net_interest_income: float | None = None
    net_interest_income_yoy: float | None = None
    efficiency_ratio_proxy: float | None = None
    provision_for_credit_losses: float | None = None
    provision_to_revenue: float | None = None
    equity_to_assets: float | None = None
    total_assets: float | None = None
    stockholders_equity: float | None = None
    bank_metric_coverage_pct: float | None = None

    # REIT-native statement-derived proxies
    reit_ffo_proxy: float | None = None
    reit_ffo_per_share_proxy: float | None = None
    reit_p_ffo_proxy: float | None = None
    reit_ffo_payout_proxy: float | None = None
    reit_net_debt_to_ebitda: float | None = None
    reit_depreciation_amortization: float | None = None
    reit_gain_loss_sale_adjustment: float | None = None
    reit_metric_coverage_pct: float | None = None

    # insurance-native statement-derived proxies
    insurance_net_investment_income: float | None = None
    insurance_claims_benefits: float | None = None
    insurance_claims_to_revenue: float | None = None
    insurance_operating_expense: float | None = None
    insurance_operating_ratio_proxy: float | None = None
    insurance_book_value_per_share_proxy: float | None = None
    insurance_equity_to_assets: float | None = None
    insurance_metric_coverage_pct: float | None = None


def _percentile_rank(value: float | None, all_values: list[float | None], invert: bool = False) -> float | None:
    clean = sorted(v for v in all_values if v is not None)
    if value is None or not clean:
        return None
    rank = sum(1 for v in clean if v <= value) / len(clean)
    pct = rank * 100
    return 100 - pct if invert else pct


def _avg(values):
    vals = [v for v in values if v is not None]
    return sum(vals) / len(vals) if vals else None


def _median_any(values):
    clean = sorted(float(v) for v in values if v is not None)
    if not clean:
        return None
    n=len(clean); mid=n//2
    return clean[mid] if n%2 else (clean[mid-1]+clean[mid])/2


def _median_positive(values):
    clean = sorted(float(v) for v in values if v is not None and v > 0)
    if not clean:
        return None
    n = len(clean)
    mid = n // 2
    return clean[mid] if n % 2 else (clean[mid - 1] + clean[mid]) / 2


def _relative_pct(value, benchmark):
    if value is None or benchmark is None or value <= 0 or benchmark <= 0:
        return None
    return (value / benchmark - 1.0) * 100.0


def _positive_score(value: float | None) -> float | None:
    if value is None:
        return None
    return 100.0 if value > 0 else 0.0


def _sum_recent(series, count=4):
    """Sum the most recent fully-populated observations; otherwise stay missing."""
    if not isinstance(series, list) or len(series) < count:
        return None
    vals=[]
    for row in series[:count]:
        try:
            v=row.get("value") if isinstance(row, dict) else None
            if v is None:
                return None
            vals.append(float(v))
        except Exception:
            return None
    return sum(vals)



def _score_model_for(r: RawMetrics) -> str:
    sector = (r.sector or "").lower()
    industry = (r.industry or "").lower()
    if "real estate" in sector or "reit" in industry:
        return "reit"
    if "financial" in sector:
        if any(k in industry for k in ("bank", "credit", "savings", "thrift")):
            return "bank"
        if any(k in industry for k in ("insurance", "insur")):
            return "insurance"
    if "utilit" in sector:
        return "utility"
    if "energy" in sector:
        return "energy"
    if "healthcare" in sector and any(k in industry for k in ("biotech", "biotechnology", "drug", "pharma")):
        return "biotech"
    if "technology" in sector and (
        (r.revenue_growth is not None and r.revenue_growth >= 0.15)
        or any(k in industry for k in ("software", "semiconductor", "internet", "cloud", "cyber"))
    ):
        return "growth_tech"
    return "general"


def _weighted(parts):
    present = [(value, weight) for value, weight in parts if value is not None]
    if not present:
        return None
    wsum = sum(weight for _, weight in present)
    return sum(value * weight for value, weight in present) / wsum


AI_EXPOSED_TICKERS = {
    "MSFT", "NVDA", "GOOGL", "GOOG", "AMZN", "META", "ORCL", "AVGO",
    "AMD", "PLTR", "CRM", "NOW", "SNOW", "SMCI", "ARM", "TSM", "ASML",
}


def score_universe(raw: list[RawMetrics]) -> list[ScoredTicker]:
    equities = [r for r in raw if r.quote_type not in ("ETF", "CRYPTO") and r.error is None]
    etfs = [r for r in raw if r.quote_type == "ETF" and r.error is None]
    cryptos = [r for r in raw if r.quote_type == "CRYPTO" and r.error is None]

    def arr(attr):
        return [getattr(r, attr) for r in equities]

    fcf_yields = [
        (r.free_cash_flow / r.market_cap) if r.free_cash_flow is not None and r.market_cap and r.market_cap > 0 else None
        for r in equities
    ]
    net_cash_values = [
        ((r.total_cash or 0) - (r.total_debt or 0)) if (r.total_cash is not None or r.total_debt is not None) else None
        for r in equities
    ]
    net_cash_to_cap = [
        (v / r.market_cap) if v is not None and r.market_cap and r.market_cap > 0 else None
        for v, r in zip(net_cash_values, equities)
    ]

    # TTM statement-derived diagnostics. These deliberately remain None when
    # four comparable quarters are not available.
    ttm_net_incomes = [_sum_recent(r.quarterly_net_income, 4) for r in equities]
    ttm_revenues = [_sum_recent(r.quarterly_revenue, 4) for r in equities]
    cash_conversion = [
        (r.operating_cash_flow / ni) if ni is not None and ni > 0 and r.operating_cash_flow is not None else None
        for r, ni in zip(equities, ttm_net_incomes)
    ]
    accrual_ratios = [
        ((ni - r.operating_cash_flow) / abs(r.total_assets))
        if ni is not None and r.operating_cash_flow is not None and r.total_assets not in (None, 0) else None
        for r, ni in zip(equities, ttm_net_incomes)
    ]
    fcf_margins = [
        (r.free_cash_flow / rev) if r.free_cash_flow is not None and rev not in (None, 0) else None
        for r, rev in zip(equities, ttm_revenues)
    ]

    out: list[ScoredTicker] = []

    for idx, r in enumerate(equities):
        coverage = None
        zombie = "unknown"
        if r.ebit is not None and r.interest_expense is not None:
            if r.interest_expense == 0:
                zombie, coverage = "no", None
            else:
                coverage = r.ebit / r.interest_expense
                zombie = "yes" if coverage < 1.0 else "no"

        quality = _avg([
            _percentile_rank(r.roe, arr("roe")),
            _percentile_rank(r.roa, arr("roa")),
            _percentile_rank(r.profit_margin, arr("profit_margin")),
            _percentile_rank(r.operating_margin, arr("operating_margin")),
            _percentile_rank(r.gross_margin, arr("gross_margin")),
        ])

        growth = _avg([
            _percentile_rank(r.revenue_growth, arr("revenue_growth")),
            _percentile_rank(r.earnings_growth, arr("earnings_growth")),
            _percentile_rank(r.earnings_quarterly_growth, arr("earnings_quarterly_growth")),
        ])

        coverage_pct = None
        if coverage is not None:
            coverages = []
            for x in equities:
                if x.ebit is not None and x.interest_expense not in (None, 0):
                    coverages.append(x.ebit / x.interest_expense)
            coverage_pct = _percentile_rank(coverage, coverages)

        balance = _avg([
            _percentile_rank(r.current_ratio, arr("current_ratio")),
            _percentile_rank(r.quick_ratio, arr("quick_ratio")),
            _percentile_rank(r.debt_to_equity, arr("debt_to_equity"), invert=True),
            _percentile_rank(net_cash_to_cap[idx], net_cash_to_cap),
            coverage_pct,
        ])

        fcf_yield = fcf_yields[idx]
        # Extremely high FCF yields are often distress/data/capital-structure signals.
        # Do not reward >30% automatically until an independent source confirms it.
        fcf_yield_for_score = fcf_yield if fcf_yield is None or abs(fcf_yield) <= 0.30 else None
        plausible_fcf_yields = [v if v is None or abs(v) <= 0.30 else None for v in fcf_yields]
        cashflow = _avg([
            _percentile_rank(fcf_yield_for_score, plausible_fcf_yields),
            _positive_score(r.operating_cash_flow),
        ])

        value_parts = []
        for value, values in [
            (r.trailing_pe, arr("trailing_pe")),
            (r.forward_pe, arr("forward_pe")),
            (r.price_to_book, arr("price_to_book")),
            (r.enterprise_to_ebitda, arr("enterprise_to_ebitda")),
            (r.peg_ratio, arr("peg_ratio")),
        ]:
            value_parts.append(_percentile_rank(value, values, invert=True) if value is not None and value > 0 else None)
        value = _avg(value_parts)

        stability = _percentile_rank(r.beta, arr("beta"), invert=True) if r.beta is not None else None

        model = _score_model_for(r)
        income = _percentile_rank(r.dividend_yield, arr("dividend_yield")) if r.dividend_yield is not None else None

        # Sector-aware score packs. These deliberately use only metrics that are
        # economically meaningful for the business model. Specialist packs are
        # marked as proxy models until regulatory / FFO-AFFO datasets are added.
        if model == "bank":
            bank_quality = _avg([
                _percentile_rank(r.roe, arr("roe")),
                _percentile_rank(r.roa, arr("roa")),
                _percentile_rank(r.profit_margin, arr("profit_margin")),
            ])
            bank_efficiency = _percentile_rank(r.efficiency_ratio_proxy, arr("efficiency_ratio_proxy"), invert=True)
            bank_asset_quality = _percentile_rank(r.provision_to_revenue, arr("provision_to_revenue"), invert=True)
            bank_capital = _percentile_rank(r.equity_to_assets, arr("equity_to_assets"))
            bank_nii_growth = _percentile_rank(r.net_interest_income_yoy, arr("net_interest_income_yoy"))
            bank_growth = _avg([growth, bank_nii_growth])
            bank_value = _avg([
                _percentile_rank(r.price_to_book, arr("price_to_book"), invert=True) if r.price_to_book and r.price_to_book > 0 else None,
                _percentile_rank(r.trailing_pe, arr("trailing_pe"), invert=True) if r.trailing_pe and r.trailing_pe > 0 else None,
                _percentile_rank(r.forward_pe, arr("forward_pe"), invert=True) if r.forward_pe and r.forward_pe > 0 else None,
            ])
            composite = _weighted([(bank_quality,.22),(bank_efficiency,.13),(bank_asset_quality,.10),(bank_capital,.15),(bank_growth,.15),(bank_value,.15),(income,.05),(stability,.05)])
            quality = _avg([bank_quality, bank_efficiency, bank_asset_quality, bank_capital])
            growth = bank_growth
            value = bank_value
            balance = bank_capital
            score_dimensions = {"Bank Quality": bank_quality, "Efficiency": bank_efficiency, "Asset Quality": bank_asset_quality, "Capital Proxy": bank_capital, "Growth": bank_growth, "Valuation": bank_value, "Income": income, "Stability": stability}
            model_note = "Bank-native proxy model: profitability, statement-derived efficiency, credit-loss provision intensity, equity/assets capital proxy, net-interest-income growth, P/B-P/E valuation and income. CET1 and NPL remain unavailable because they require regulatory filings."
        elif model == "reit":
            # Compare REIT-native metrics against REIT peers only. This avoids
            # ranking P/FFO or payout against structurally unrelated companies.
            reit_peers = [x for x in equities if _score_model_for(x) == "reit"]
            reit_ffo_quality = _percentile_rank(r.reit_ffo_per_share_proxy, [x.reit_ffo_per_share_proxy for x in reit_peers])
            reit_quality = _avg([
                reit_ffo_quality,
                _percentile_rank(r.roe, [x.roe for x in reit_peers]),
                _percentile_rank(r.profit_margin, [x.profit_margin for x in reit_peers]),
            ])
            reit_leverage = _avg([
                _percentile_rank(r.reit_net_debt_to_ebitda, [x.reit_net_debt_to_ebitda for x in reit_peers], invert=True),
                coverage_pct,
            ])
            reit_value = _avg([
                _percentile_rank(r.reit_p_ffo_proxy, [x.reit_p_ffo_proxy for x in reit_peers], invert=True) if r.reit_p_ffo_proxy and r.reit_p_ffo_proxy > 0 else None,
                _percentile_rank(r.price_to_book, [x.price_to_book for x in reit_peers], invert=True) if r.price_to_book and r.price_to_book > 0 else None,
            ])
            reit_distribution = _avg([
                income,
                _percentile_rank(r.reit_ffo_payout_proxy, [x.reit_ffo_payout_proxy for x in reit_peers], invert=True) if r.reit_ffo_payout_proxy is not None and r.reit_ffo_payout_proxy >= 0 else None,
            ])
            composite = _weighted([(reit_quality,.22),(growth,.16),(reit_leverage,.20),(reit_value,.20),(reit_distribution,.17),(stability,.05)])
            quality, balance, value = reit_quality, reit_leverage, reit_value
            score_dimensions = {"REIT Quality": reit_quality, "Growth": growth, "Leverage": reit_leverage, "P/FFO Value": reit_value, "Distribution": reit_distribution, "Stability": stability}
            model_note = "REIT-native proxy model: statement-derived FFO proxy, P/FFO proxy, FFO payout proxy, net-debt/EBITDA, growth and distributions. AFFO, NAV and occupancy remain unavailable rather than inferred."
        elif model == "insurance":
            insurance_peers = [x for x in equities if _score_model_for(x) == "insurance"]
            ins_quality = _avg([
                _percentile_rank(r.roe, [x.roe for x in insurance_peers]),
                _percentile_rank(r.roa, [x.roa for x in insurance_peers]),
                _percentile_rank(r.profit_margin, [x.profit_margin for x in insurance_peers]),
            ])
            ins_underwriting = _avg([
                _percentile_rank(r.insurance_claims_to_revenue, [x.insurance_claims_to_revenue for x in insurance_peers], invert=True),
                _percentile_rank(r.insurance_operating_ratio_proxy, [x.insurance_operating_ratio_proxy for x in insurance_peers], invert=True),
            ])
            ins_capital = _avg([
                _percentile_rank(r.insurance_equity_to_assets, [x.insurance_equity_to_assets for x in insurance_peers]),
                _percentile_rank(r.debt_to_equity, [x.debt_to_equity for x in insurance_peers], invert=True),
            ])
            ins_value = _avg([
                _percentile_rank(r.price_to_book, [x.price_to_book for x in insurance_peers], invert=True) if r.price_to_book and r.price_to_book > 0 else None,
                _percentile_rank(r.trailing_pe, [x.trailing_pe for x in insurance_peers], invert=True) if r.trailing_pe and r.trailing_pe > 0 else None,
            ])
            ins_income_quality = _avg([
                income,
                _positive_score(r.insurance_net_investment_income),
            ])
            composite = _weighted([(ins_quality,.22),(ins_underwriting,.18),(ins_capital,.18),(growth,.12),(ins_value,.17),(ins_income_quality,.08),(stability,.05)])
            quality, balance, value = _avg([ins_quality, ins_underwriting]), ins_capital, ins_value
            score_dimensions = {"Insurance Quality": ins_quality, "Underwriting Proxy": ins_underwriting, "Capital Proxy": ins_capital, "Growth": growth, "Valuation": ins_value, "Income": ins_income_quality, "Stability": stability}
            model_note = "Insurance-native proxy model: profitability, claims/cost-load proxies, accounting capitalisation, growth, P/B-P/E valuation and income. It does not fabricate statutory combined ratio or solvency capital."
        elif model == "utility":
            peers = [x for x in equities if _score_model_for(x) == "utility"]
            util_quality = _avg([
                _percentile_rank(r.roe, [x.roe for x in peers]),
                _percentile_rank(r.operating_margin, [x.operating_margin for x in peers]),
                _percentile_rank(r.roce_proxy, [x.roce_proxy for x in peers]),
            ])
            util_balance = _avg([
                _percentile_rank(r.debt_to_equity, [x.debt_to_equity for x in peers], invert=True),
                coverage_pct,
            ])
            util_income = _avg([
                _percentile_rank(r.dividend_yield, [x.dividend_yield for x in peers]),
                _percentile_rank(r.payout_ratio, [x.payout_ratio for x in peers], invert=True) if r.payout_ratio is not None else None,
            ])
            util_value = _avg([
                _percentile_rank(r.forward_pe, [x.forward_pe for x in peers], invert=True) if r.forward_pe and r.forward_pe > 0 else None,
                _percentile_rank(r.trailing_pe, [x.trailing_pe for x in peers], invert=True) if r.trailing_pe and r.trailing_pe > 0 else None,
                _percentile_rank(r.price_to_book, [x.price_to_book for x in peers], invert=True) if r.price_to_book and r.price_to_book > 0 else None,
            ])
            util_cash = _avg([cashflow, _positive_score(r.operating_cash_flow)])
            composite = _weighted([(util_quality,.18),(util_balance,.22),(util_income,.18),(util_value,.17),(growth,.10),(stability,.10),(util_cash,.05)])
            quality, balance, value, cashflow = util_quality, util_balance, util_value, util_cash
            score_dimensions = {"Utility Quality":util_quality,"Balance":util_balance,"Income":util_income,"Valuation":util_value,"Growth":growth,"Stability":stability,"Cash Flow":util_cash}
            model_note = "Utility model: balance-sheet resilience, regulated-style income durability, profitability, peer valuation and stability receive more weight than headline growth."
        elif model == "energy":
            peers = [x for x in equities if _score_model_for(x) == "energy"]
            peer_fcf = [(x.free_cash_flow/x.market_cap) if x.free_cash_flow is not None and x.market_cap and x.market_cap>0 else None for x in peers]
            energy_quality = _avg([
                _percentile_rank(r.roe, [x.roe for x in peers]),
                _percentile_rank(r.operating_margin, [x.operating_margin for x in peers]),
                _percentile_rank(r.roce_proxy, [x.roce_proxy for x in peers]),
            ])
            energy_cash = _avg([
                _percentile_rank(fcf_yield_for_score, peer_fcf),
                _positive_score(r.operating_cash_flow),
            ])
            energy_balance = _avg([
                _percentile_rank(r.debt_to_equity, [x.debt_to_equity for x in peers], invert=True),
                _percentile_rank(net_cash_to_cap[idx], [((x.total_cash or 0)-(x.total_debt or 0))/x.market_cap if x.market_cap and (x.total_cash is not None or x.total_debt is not None) else None for x in peers]),
                coverage_pct,
            ])
            energy_value = _avg([
                _percentile_rank(r.trailing_pe, [x.trailing_pe for x in peers], invert=True) if r.trailing_pe and r.trailing_pe>0 else None,
                _percentile_rank(r.forward_pe, [x.forward_pe for x in peers], invert=True) if r.forward_pe and r.forward_pe>0 else None,
                _percentile_rank(r.enterprise_to_ebitda, [x.enterprise_to_ebitda for x in peers], invert=True) if r.enterprise_to_ebitda and r.enterprise_to_ebitda>0 else None,
            ])
            composite = _weighted([(energy_quality,.20),(energy_cash,.22),(energy_balance,.18),(energy_value,.20),(growth,.10),(stability,.10)])
            quality,balance,value,cashflow=energy_quality,energy_balance,energy_value,energy_cash
            score_dimensions={"Energy Quality":energy_quality,"Cash Flow":energy_cash,"Balance":energy_balance,"Valuation":energy_value,"Growth":growth,"Stability":stability}
            model_note = "Energy model: cash generation, capital efficiency, leverage and peer valuation dominate; cyclical growth receives a lower weight."
        elif model == "biotech":
            peers = [x for x in equities if _score_model_for(x) == "biotech"]
            runway = (r.total_cash/abs(r.free_cash_flow)) if r.total_cash is not None and r.total_cash>0 and r.free_cash_flow is not None and r.free_cash_flow<0 else None
            runways=[(x.total_cash/abs(x.free_cash_flow)) if x.total_cash is not None and x.total_cash>0 and x.free_cash_flow is not None and x.free_cash_flow<0 else None for x in peers]
            runway_score = 100.0 if r.free_cash_flow is not None and r.free_cash_flow>=0 else _percentile_rank(runway,runways)
            biotech_cash = _percentile_rank(net_cash_to_cap[idx], [((x.total_cash or 0)-(x.total_debt or 0))/x.market_cap if x.market_cap and (x.total_cash is not None or x.total_debt is not None) else None for x in peers])
            biotech_dilution = _percentile_rank(r.diluted_shares_yoy,[x.diluted_shares_yoy for x in peers],invert=True)
            biotech_quality = _avg([
                _percentile_rank(r.gross_margin,[x.gross_margin for x in peers]),
                _percentile_rank(r.roa,[x.roa for x in peers]),
            ])
            composite = _weighted([(runway_score,.25),(biotech_cash,.15),(biotech_dilution,.20),(growth,.20),(biotech_quality,.10),(stability,.10)])
            quality=_avg([biotech_quality,runway_score]); balance=_avg([runway_score,biotech_cash]); value=None
            score_dimensions={"Cash Runway":runway_score,"Net Cash":biotech_cash,"Dilution Discipline":biotech_dilution,"Growth":growth,"Operating Quality":biotech_quality,"Stability":stability}
            model_note = "Biotech model: cash runway, net cash, dilution and operating progress dominate. Generic P/E valuation is deliberately excluded for pre-profit companies; pipeline quality/catalysts are not fabricated from accounting data."
        elif model == "growth_tech":
            peers = [x for x in equities if _score_model_for(x) == "growth_tech"]
            execution = _avg([
                _percentile_rank(r.revenue_yoy_acceleration_pp,[x.revenue_yoy_acceleration_pp for x in peers]),
                _percentile_rank(r.net_margin_yoy_change_pp,[x.net_margin_yoy_change_pp for x in peers]),
                _percentile_rank(r.eps_yoy_acceleration_pp,[x.eps_yoy_acceleration_pp for x in peers]),
            ])
            earnings_quality = _avg([
                _percentile_rank(cash_conversion[idx],cash_conversion),
                _percentile_rank(accrual_ratios[idx],accrual_ratios,invert=True),
                _percentile_rank(fcf_margins[idx],fcf_margins),
            ])
            capital_allocation = _avg([
                _percentile_rank(r.diluted_shares_yoy,[x.diluted_shares_yoy for x in peers],invert=True),
                _percentile_rank(r.roce_proxy,[x.roce_proxy for x in peers]),
            ])
            tech_value = _avg([
                _percentile_rank(r.forward_pe,[x.forward_pe for x in peers],invert=True) if r.forward_pe and r.forward_pe>0 else None,
                _percentile_rank(fcf_yield_for_score,[(x.free_cash_flow/x.market_cap) if x.free_cash_flow is not None and x.market_cap and x.market_cap>0 else None for x in peers]),
            ])
            composite = _weighted([(quality,.20),(growth,.22),(balance,.12),(cashflow,.10),(tech_value,.07),(execution,.12),(earnings_quality,.09),(capital_allocation,.05),(stability,.03)])
            value=tech_value
            score_dimensions={"Quality":quality,"Growth":growth,"Balance":balance,"Cash Flow":cashflow,"Valuation":tech_value,"Execution":execution,"Earnings Quality":earnings_quality,"Capital Allocation":capital_allocation,"Stability":stability}
            model_note = "Growth-tech model: growth, quality, execution and cash conversion dominate; valuation remains relevant but cannot overwhelm superior or deteriorating operating evidence."
        else:
            # Execution is operating momentum, deliberately separated from
            # shareholder-capital decisions so a buyback cannot disguise weak
            # underlying execution (or vice versa).
            execution = _avg([
                _percentile_rank(r.revenue_yoy_acceleration_pp, [x.revenue_yoy_acceleration_pp for x in equities]),
                _percentile_rank(r.net_margin_yoy_change_pp, [x.net_margin_yoy_change_pp for x in equities]),
                _percentile_rank(r.eps_yoy_acceleration_pp, [x.eps_yoy_acceleration_pp for x in equities]),
            ])

            earnings_quality = _avg([
                _percentile_rank(cash_conversion[idx], cash_conversion),
                _percentile_rank(accrual_ratios[idx], accrual_ratios, invert=True),
                _percentile_rank(fcf_margins[idx], fcf_margins),
            ])

            # Capital allocation rewards per-share discipline and productive
            # reinvestment. Repurchases are only a positive signal when actually
            # reported; missing buybacks are not treated as a penalty.
            buyback_signal = _positive_score(r.repurchases_last_quarter)
            dividend_cover_rank = _percentile_rank(
                r.dividend_fcf_coverage,
                [x.dividend_fcf_coverage for x in equities]
            ) if r.dividend_fcf_coverage is not None else None
            capital_allocation = _avg([
                _percentile_rank(r.diluted_shares_yoy, [x.diluted_shares_yoy for x in equities], invert=True),
                buyback_signal,
                _percentile_rank(r.roce_proxy, [x.roce_proxy for x in equities]),
                dividend_cover_rank,
            ])

            composite = _weighted([
                (quality,.18),(growth,.15),(balance,.14),(cashflow,.08),(value,.12),
                (execution,.10),(earnings_quality,.10),(capital_allocation,.08),(stability,.05)
            ])
            score_dimensions = {
                "Quality": quality, "Growth": growth, "Balance": balance, "Cash Flow": cashflow,
                "Valuation": value, "Execution": execution, "Earnings Quality": earnings_quality,
                "Capital Allocation": capital_allocation, "Stability": stability
            }
            model_note = "General company model v3: adds cash-conversion/accrual quality and separates capital allocation from operating execution."

        if model not in ("general", "growth_tech"):
            execution = None
            earnings_quality = None
            capital_allocation = None

        # v4.1 Risk Gate: weighted averages cannot wash away structural red flags.
        # Generic and explainable rules only; no ticker blacklist.
        risk_flags = []
        if zombie == "yes" and model not in ("bank", "insurance"):
            risk_flags.append("zombie_interest_coverage")
        if fcf_yield is not None and abs(fcf_yield) > 0.30:
            risk_flags.append("extreme_fcf_yield")
        if quality is not None and quality < 40:
            risk_flags.append("weak_quality")
        if r.revenue_growth is not None and r.revenue_growth < -0.15:
            risk_flags.append("revenue_contraction")
        if r.diluted_shares_yoy is not None and r.diluted_shares_yoy > 0.20:
            risk_flags.append("material_dilution")
        if r.diluted_shares_yoy is not None and r.diluted_shares_yoy > 0.50:
            risk_flags.append("severe_dilution")

        capital_flags = list(getattr(r, "capital_structure_flags", []) or [])
        for flag in capital_flags:
            if flag not in risk_flags:
                risk_flags.append(flag)
        capital_gate = str(getattr(r, "capital_structure_risk", "clear") or "clear")

        risk_gate = "clear"
        score_cap = None
        severe = any(x in risk_flags for x in ("zombie_interest_coverage", "severe_dilution"))
        if severe:
            risk_gate, score_cap = "severe", 45.0
        elif len(risk_flags) >= 2:
            risk_gate, score_cap = "high", 59.0
        elif risk_flags:
            risk_gate, score_cap = "watch", 69.0

        # Filing-derived capital structure risk gets the most restrictive cap.
        cap_by_gate = {"watch": 64.0, "high": 49.0, "severe": 35.0}
        rank = {"clear": 0, "watch": 1, "high": 2, "severe": 3}
        if capital_gate in cap_by_gate:
            ccap = cap_by_gate[capital_gate]
            score_cap = min(score_cap if score_cap is not None else 100.0, ccap)
            if rank.get(capital_gate, 0) > rank.get(risk_gate, 0):
                risk_gate = capital_gate
        if composite is not None and score_cap is not None:
            composite = min(composite, score_cap)

        metric_values = [
            r.roe, r.roa, r.profit_margin, r.operating_margin, r.gross_margin,
            r.revenue_growth, r.earnings_growth, r.earnings_quarterly_growth,
            r.free_cash_flow, r.operating_cash_flow, r.current_ratio, r.quick_ratio,
            r.debt_to_equity, r.total_cash, r.total_debt, r.trailing_pe, r.forward_pe,
            r.price_to_book, r.enterprise_to_ebitda, r.peg_ratio, r.beta,
            r.revenue_yoy_acceleration_pp, r.net_margin_yoy_change_pp,
            r.diluted_shares_yoy, r.roce_proxy, cash_conversion[idx],
            accrual_ratios[idx], fcf_margins[idx], r.repurchases_last_quarter,
            r.dividend_fcf_coverage,
        ]
        metric_coverage = sum(v is not None for v in metric_values) / len(metric_values) * 100
        confidence = "high" if metric_coverage >= 70 else "medium" if metric_coverage >= 40 else "low"
        if risk_gate == "severe":
            confidence = "low"
        elif risk_gate == "high" and confidence == "high":
            confidence = "medium"
        if model == "bank" and confidence == "high":
            confidence = "medium"
        if model == "insurance":
            if (r.insurance_metric_coverage_pct or 0) < 40:
                confidence = "low"
            elif confidence == "high":
                confidence = "medium"
        if model == "reit" and confidence == "high" and (r.reit_metric_coverage_pct or 0) < 60:
            confidence = "medium"

        # Peer-relative valuation context. We deliberately compare within sector,
        # not across the full market, because structurally different sectors trade
        # at different multiples. A minimum of 4 peers avoids pretending that a
        # tiny sample is a meaningful benchmark.
        peers = [x for x in equities if x.ticker != r.ticker and x.sector and x.sector == r.sector]
        peer_count = len(peers)
        sector_pe = _median_positive([x.trailing_pe for x in peers]) if peer_count >= 4 else None
        sector_fpe = _median_positive([x.forward_pe for x in peers]) if peer_count >= 4 else None
        sector_pb = _median_positive([x.price_to_book for x in peers]) if peer_count >= 4 else None
        sector_ev = _median_positive([x.enterprise_to_ebitda for x in peers]) if peer_count >= 4 else None
        sector_roe = _median_any([x.roe for x in peers]) if peer_count >= 4 else None
        sector_opm = _median_any([x.operating_margin for x in peers]) if peer_count >= 4 else None
        sector_gm = _median_any([x.gross_margin for x in peers]) if peer_count >= 4 else None
        sector_roce = _median_any([x.roce_proxy for x in peers]) if peer_count >= 4 else None
        sector_div = _median_any([x.dividend_yield for x in peers]) if peer_count >= 4 else None
        sector_fcf = _median_positive([(x.free_cash_flow/x.market_cap) if x.free_cash_flow is not None and x.market_cap and x.market_cap>0 else None for x in peers]) if peer_count >= 4 else None
        quality_value = _avg([quality, value])

        net_cash = net_cash_values[idx]
        out.append(ScoredTicker(
            ticker=r.ticker, name=r.name, business_summary=r.business_summary, sector=r.sector, industry=r.industry,
            market_cap=r.market_cap, currency=r.currency, quote_type=r.quote_type,
            score=round(composite, 1) if composite is not None else None,
            data_confidence=confidence, data_coverage_pct=round(metric_coverage, 1),
            zombie=zombie, interest_coverage=round(coverage, 2) if coverage is not None else None,
            profitability_pct=round(quality, 1) if quality is not None else None,
            leverage_pct=round(balance, 1) if balance is not None else None,
            value_pct=round(value, 1) if value is not None else None,
            stability_pct=round(stability, 1) if stability is not None else None,
            quality_pct=round(quality, 1) if quality is not None else None,
            growth_pct=round(growth, 1) if growth is not None else None,
            balance_pct=round(balance, 1) if balance is not None else None,
            cashflow_pct=round(cashflow, 1) if cashflow is not None else None,
            execution_pct=round(execution, 1) if execution is not None else None,
            earnings_quality_pct=round(earnings_quality, 1) if earnings_quality is not None else None,
            capital_allocation_pct=round(capital_allocation, 1) if capital_allocation is not None else None,
            roe=r.roe, roa=r.roa, profit_margin=r.profit_margin,
            operating_margin=r.operating_margin, gross_margin=r.gross_margin,
            revenue_growth=r.revenue_growth, earnings_growth=r.earnings_growth,
            earnings_quarterly_growth=r.earnings_quarterly_growth,
            free_cash_flow=r.free_cash_flow, operating_cash_flow=r.operating_cash_flow,
            fcf_yield=round(fcf_yield, 6) if fcf_yield is not None else None,
            current_ratio=r.current_ratio, quick_ratio=r.quick_ratio,
            debt_to_equity=r.debt_to_equity, net_cash=net_cash,
            trailing_pe=r.trailing_pe, forward_pe=r.forward_pe,
            price_to_book=r.price_to_book, enterprise_to_ebitda=r.enterprise_to_ebitda,
            peg_ratio=r.peg_ratio, dividend_yield=r.dividend_yield,
            payout_ratio=r.payout_ratio, beta=r.beta, current_price=r.current_price,
            cash_conversion_ratio=round(cash_conversion[idx],4) if cash_conversion[idx] is not None else None,
            accrual_ratio=round(accrual_ratios[idx],6) if accrual_ratios[idx] is not None else None,
            fcf_margin=round(fcf_margins[idx],6) if fcf_margins[idx] is not None else None,
            ttm_net_income=ttm_net_incomes[idx], ttm_revenue=ttm_revenues[idx],
            diluted_shares_yoy=r.diluted_shares_yoy, repurchases_last_quarter=r.repurchases_last_quarter,
            dividend_fcf_coverage=r.dividend_fcf_coverage, roce_proxy=r.roce_proxy,
            peer_count=peer_count,
            sector_trailing_pe_median=round(sector_pe, 2) if sector_pe is not None else None,
            trailing_pe_vs_sector_pct=round(_relative_pct(r.trailing_pe, sector_pe), 1) if _relative_pct(r.trailing_pe, sector_pe) is not None else None,
            sector_forward_pe_median=round(sector_fpe, 2) if sector_fpe is not None else None,
            forward_pe_vs_sector_pct=round(_relative_pct(r.forward_pe, sector_fpe), 1) if _relative_pct(r.forward_pe, sector_fpe) is not None else None,
            sector_pb_median=round(sector_pb, 2) if sector_pb is not None else None,
            pb_vs_sector_pct=round(_relative_pct(r.price_to_book, sector_pb), 1) if _relative_pct(r.price_to_book, sector_pb) is not None else None,
            sector_ev_ebitda_median=round(sector_ev, 2) if sector_ev is not None else None,
            ev_ebitda_vs_sector_pct=round(_relative_pct(r.enterprise_to_ebitda, sector_ev), 1) if _relative_pct(r.enterprise_to_ebitda, sector_ev) is not None else None,
            quality_value_score=round(quality_value, 1) if quality_value is not None else None,
            sector_roe_median=round(sector_roe,4) if sector_roe is not None else None,
            sector_operating_margin_median=round(sector_opm,4) if sector_opm is not None else None,
            sector_gross_margin_median=round(sector_gm,4) if sector_gm is not None else None,
            sector_roce_proxy_median=round(sector_roce,4) if sector_roce is not None else None,
            sector_dividend_yield_median=round(sector_div,4) if sector_div is not None else None,
            sector_fcf_yield_median=round(sector_fcf,6) if sector_fcf is not None else None,
            score_model=model, score_model_note=model_note,
            score_dimensions={k: (round(v,1) if v is not None else None) for k,v in score_dimensions.items()},
            risk_flags=risk_flags, risk_gate=risk_gate, score_cap=score_cap,
            net_interest_income=r.net_interest_income, net_interest_income_yoy=r.net_interest_income_yoy,
            efficiency_ratio_proxy=r.efficiency_ratio_proxy,
            provision_for_credit_losses=r.provision_for_credit_losses, provision_to_revenue=r.provision_to_revenue,
            equity_to_assets=r.equity_to_assets, total_assets=r.total_assets, stockholders_equity=r.stockholders_equity,
            bank_metric_coverage_pct=r.bank_metric_coverage_pct,
            reit_ffo_proxy=r.reit_ffo_proxy, reit_ffo_per_share_proxy=r.reit_ffo_per_share_proxy,
            reit_p_ffo_proxy=r.reit_p_ffo_proxy, reit_ffo_payout_proxy=r.reit_ffo_payout_proxy,
            reit_net_debt_to_ebitda=r.reit_net_debt_to_ebitda,
            reit_depreciation_amortization=r.reit_depreciation_amortization,
            reit_gain_loss_sale_adjustment=r.reit_gain_loss_sale_adjustment,
            reit_metric_coverage_pct=r.reit_metric_coverage_pct,
            insurance_net_investment_income=r.insurance_net_investment_income,
            insurance_claims_benefits=r.insurance_claims_benefits,
            insurance_claims_to_revenue=r.insurance_claims_to_revenue,
            insurance_operating_expense=r.insurance_operating_expense,
            insurance_operating_ratio_proxy=r.insurance_operating_ratio_proxy,
            insurance_book_value_per_share_proxy=r.insurance_book_value_per_share_proxy,
            insurance_equity_to_assets=r.insurance_equity_to_assets,
            insurance_metric_coverage_pct=r.insurance_metric_coverage_pct,
        ))

    for r in cryptos:
        out.append(ScoredTicker(
            ticker=r.ticker, name=r.name, business_summary=r.business_summary, sector="Crypto", industry="Digital Assets",
            market_cap=r.market_cap, currency=r.currency, quote_type="CRYPTO",
            score=None, data_confidence="low", data_coverage_pct=0,
            zombie="unknown", interest_coverage=None,
            profitability_pct=None, leverage_pct=None, value_pct=None, stability_pct=None,
            quality_pct=None, growth_pct=None, balance_pct=None, cashflow_pct=None, execution_pct=None,
            current_price=r.current_price,
        ))

    for r in etfs:
        ai_pct = None
        if r.top_holdings:
            # top_holdings is stored by fundamentals.py as a list of dicts:
            # {"symbol": ..., "name": ..., "weight": ...}. Older cached data
            # may still contain tuple/list pairs, so accept both representations.
            ai_weight = 0.0
            found_weight = False
            for holding in r.top_holdings:
                sym = None
                weight = None
                if isinstance(holding, dict):
                    sym = holding.get("symbol") or holding.get("ticker")
                    weight = holding.get("weight")
                    if weight is None:
                        weight = holding.get("holding_percent")
                    if weight is None:
                        weight = holding.get("Holding Percent")
                elif isinstance(holding, (list, tuple)) and len(holding) >= 2:
                    sym, weight = holding[0], holding[1]

                try:
                    w = float(weight) if weight is not None else None
                except (TypeError, ValueError):
                    w = None

                if sym and w is not None and str(sym).upper() in AI_EXPOSED_TICKERS:
                    ai_weight += w
                    found_weight = True

            if found_weight:
                ai_pct = round(ai_weight * 100, 1)
        out.append(ScoredTicker(
            ticker=r.ticker, name=r.name, business_summary=r.business_summary, sector=r.sector, industry=r.industry,
            market_cap=r.market_cap, currency=r.currency, quote_type="ETF",
            score=None, data_confidence="low", data_coverage_pct=0,
            zombie="unknown", interest_coverage=None,
            profitability_pct=None, leverage_pct=None, value_pct=None, stability_pct=None,
            quality_pct=None, growth_pct=None, balance_pct=None, cashflow_pct=None, execution_pct=None,
            expense_ratio=r.expense_ratio, ai_exposure_pct=ai_pct, current_price=r.current_price,
        ))

    return out
