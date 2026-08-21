"""
score.py — explainable multi-factor investment scoring engine.

The score is cross-sectional: each metric is ranked against the currently
fetched equity universe. It is a screening model, not a return forecast.
Missing data are excluded rather than treated as zero.

Dimensions / weights:
  Quality       25%  ROE, ROA, net/operating/gross margins
  Growth        20%  revenue and earnings growth
  Balance       20%  liquidity, debt/equity, net cash, interest coverage
  Cash flow     10%  free-cash-flow yield, operating cash flow positivity
  Valuation     15%  trailing/forward P-E, P/B, EV/EBITDA, PEG
  Stability     10%  beta (lower is better)

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
    score_model: str = "general"
    score_model_note: str | None = None
    score_dimensions: dict[str, float | None] | None = None

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
        cashflow = _avg([
            _percentile_rank(fcf_yield, fcf_yields),
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
        else:
            composite = _weighted([(quality,.25),(growth,.20),(balance,.20),(cashflow,.10),(value,.15),(stability,.10)])
            score_dimensions = {"Quality": quality, "Growth": growth, "Balance": balance, "Cash Flow": cashflow, "Valuation": value, "Stability": stability}
            model_note = "General company model: quality, growth, balance sheet, cash flow, valuation and stability."

        if composite is not None and zombie == "yes" and model not in ("bank", "insurance"):
            composite = min(composite, 45.0)

        metric_values = [
            r.roe, r.roa, r.profit_margin, r.operating_margin, r.gross_margin,
            r.revenue_growth, r.earnings_growth, r.earnings_quarterly_growth,
            r.free_cash_flow, r.operating_cash_flow, r.current_ratio, r.quick_ratio,
            r.debt_to_equity, r.total_cash, r.total_debt, r.trailing_pe, r.forward_pe,
            r.price_to_book, r.enterprise_to_ebitda, r.peg_ratio, r.beta,
        ]
        metric_coverage = sum(v is not None for v in metric_values) / len(metric_values) * 100
        confidence = "high" if metric_coverage >= 70 else "medium" if metric_coverage >= 40 else "low"
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
            score_model=model, score_model_note=model_note,
            score_dimensions={k: (round(v,1) if v is not None else None) for k,v in score_dimensions.items()},
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
            quality_pct=None, growth_pct=None, balance_pct=None, cashflow_pct=None,
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
            quality_pct=None, growth_pct=None, balance_pct=None, cashflow_pct=None,
            expense_ratio=r.expense_ratio, ai_exposure_pct=ai_pct, current_price=r.current_price,
        ))

    return out
