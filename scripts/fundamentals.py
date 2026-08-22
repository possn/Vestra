"""
fundamentals.py — pulls raw market/fundamental metrics per ticker from yfinance.

All fields are nullable by design. Yahoo/yfinance coverage varies materially by
country and security type; missing data must never be interpreted as zero.
"""
from __future__ import annotations

import logging
import time
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

import yfinance as yf

log = logging.getLogger("fundamentals")


@dataclass
class RawMetrics:
    ticker: str
    name: str | None = None
    business_summary: str | None = None
    sector: str | None = None
    industry: str | None = None
    market_cap: float | None = None
    currency: str | None = None
    quote_type: str | None = None

    # profitability / quality
    roe: float | None = None
    roa: float | None = None
    profit_margin: float | None = None
    operating_margin: float | None = None
    gross_margin: float | None = None

    # growth
    revenue_growth: float | None = None
    earnings_growth: float | None = None
    earnings_quarterly_growth: float | None = None

    # quarterly growth / shareholder structure intelligence
    quarterly_revenue: list[dict] = field(default_factory=list)
    quarterly_net_income: list[dict] = field(default_factory=list)
    quarterly_diluted_shares: list[dict] = field(default_factory=list)
    quarterly_eps: list[dict] = field(default_factory=list)
    quarterly_rnd: list[dict] = field(default_factory=list)
    revenue_yoy_latest: float | None = None
    revenue_yoy_prior: float | None = None
    revenue_yoy_acceleration_pp: float | None = None
    net_income_yoy_latest: float | None = None
    net_income_yoy_prior: float | None = None
    net_income_yoy_acceleration_pp: float | None = None
    diluted_shares_yoy: float | None = None
    net_margin_latest: float | None = None
    net_margin_yoy_change_pp: float | None = None
    net_margin_yoy_change_prior_pp: float | None = None
    repurchases_last_quarter: float | None = None
    eps_yoy_latest: float | None = None
    eps_yoy_prior: float | None = None
    eps_yoy_acceleration_pp: float | None = None
    rnd_latest_quarter: float | None = None
    rnd_yoy: float | None = None
    rnd_to_revenue: float | None = None
    roce_proxy: float | None = None
    dividend_fcf_coverage: float | None = None
    annual_quality_history: list[dict] = field(default_factory=list)
    annual_dividend_history: list[dict] = field(default_factory=list)

    # cash flow
    free_cash_flow: float | None = None
    operating_cash_flow: float | None = None

    # cash / leverage
    current_ratio: float | None = None
    quick_ratio: float | None = None
    debt_to_equity: float | None = None
    total_cash: float | None = None
    total_debt: float | None = None
    ebit: float | None = None
    interest_expense: float | None = None

    # valuation
    trailing_pe: float | None = None
    forward_pe: float | None = None
    price_to_book: float | None = None
    enterprise_to_ebitda: float | None = None
    peg_ratio: float | None = None
    current_price: float | None = None

    # shareholder return
    dividend_yield: float | None = None
    payout_ratio: float | None = None

    # market risk
    beta: float | None = None

    # bank-specific statement-derived metrics (proxies, not regulatory ratios)
    net_interest_income: float | None = None
    net_interest_income_yoy: float | None = None
    efficiency_ratio_proxy: float | None = None
    provision_for_credit_losses: float | None = None
    provision_to_revenue: float | None = None
    equity_to_assets: float | None = None
    total_assets: float | None = None
    stockholders_equity: float | None = None
    bank_metric_coverage_pct: float | None = None

    # REIT-specific statement-derived metrics. FFO is an explicit proxy built
    # from public GAAP statements; AFFO/NAV/occupancy are never fabricated.
    ebitda: float | None = None
    reit_ffo_proxy: float | None = None
    reit_ffo_per_share_proxy: float | None = None
    reit_p_ffo_proxy: float | None = None
    reit_ffo_payout_proxy: float | None = None
    reit_net_debt_to_ebitda: float | None = None
    reit_depreciation_amortization: float | None = None
    reit_gain_loss_sale_adjustment: float | None = None
    reit_metric_coverage_pct: float | None = None

    # Insurance-specific statement-derived proxies. These are deliberately
    # labelled proxies because generic Yahoo statements do not expose
    # regulator-specific solvency metrics consistently across jurisdictions.
    insurance_net_investment_income: float | None = None
    insurance_claims_benefits: float | None = None
    insurance_claims_to_revenue: float | None = None
    insurance_operating_expense: float | None = None
    insurance_operating_ratio_proxy: float | None = None
    insurance_book_value_per_share_proxy: float | None = None
    insurance_equity_to_assets: float | None = None
    insurance_metric_coverage_pct: float | None = None

    # ETF-specific. FundsData is optional and Yahoo coverage varies by listing.
    expense_ratio: float | None = None
    top_holdings: list[dict] = field(default_factory=list)
    fund_family: str | None = None
    fund_category: str | None = None
    fund_legal_type: str | None = None
    fund_inception_date: str | None = None
    fund_description: str | None = None
    fund_total_assets: float | None = None
    fund_asset_classes: dict = field(default_factory=dict)
    fund_sector_weightings: dict = field(default_factory=dict)

    error: str | None = None


def _safe_get(d: dict, *keys, default=None):
    for k in keys:
        v = d.get(k)
        if v is not None:
            return v
    return default


def _as_float(x):
    if x is None:
        return None
    try:
        f = float(x)
    except (TypeError, ValueError):
        return None
    if f != f or f in (float("inf"), float("-inf")):
        return None
    return f


def _yahoo_symbol(ticker: str) -> str:
    """Translate broker/DivTracker symbols to Yahoo symbols without changing
    the canonical ticker stored by Finscanner. Crypto positions are exported
    by DivTracker as e.g. BTC.CC while Yahoo uses BTC-USD."""
    t = str(ticker or "").strip().upper()
    if t.endswith(".CC") and len(t) > 3:
        return t[:-3] + "-USD"
    return t


def _apply_fast_fallback(t, m: RawMetrics) -> bool:
    """Recover identity/price when Yahoo's heavy `info` endpoint is throttled.
    A portfolio position should remain recognisable/valuable even when full
    fundamentals are temporarily unavailable. Returns True if minimally usable.
    """
    got = False
    try:
        fi = t.fast_info
        if fi is not None:
            for key in ("last_price", "previous_close"):
                try:
                    v = _as_float(fi.get(key) if hasattr(fi, "get") else getattr(fi, key, None))
                except Exception:
                    v = None
                if v is not None and v > 0:
                    m.current_price = m.current_price or v
                    got = True
                    break
            try:
                cur = fi.get("currency") if hasattr(fi, "get") else getattr(fi, "currency", None)
                if cur:
                    m.currency = m.currency or str(cur)
            except Exception:
                pass
            try:
                cap = _as_float(fi.get("market_cap") if hasattr(fi, "get") else getattr(fi, "market_cap", None))
                if cap is not None:
                    m.market_cap = m.market_cap or cap
            except Exception:
                pass
    except Exception:
        pass
    if m.current_price is None:
        try:
            hist = t.history(period="5d", auto_adjust=False)
            if hist is not None and not hist.empty and "Close" in hist:
                close = hist["Close"].dropna()
                if not close.empty:
                    m.current_price = _as_float(close.iloc[-1])
                    got = m.current_price is not None
        except Exception:
            pass
    return got



def _row_value(frame, labels, col_index=0):
    if frame is None or getattr(frame, "empty", True):
        return None
    for label in labels:
        if label in frame.index:
            try:
                return _as_float(frame.loc[label].iloc[col_index])
            except Exception:
                return None
    return None


def _row_series(frame, labels, limit=6):
    if frame is None or getattr(frame, "empty", True):
        return []
    for label in labels:
        if label in frame.index:
            vals=[]
            for c in list(frame.columns)[:limit]:
                try:
                    v=_as_float(frame.loc[label, c])
                    vals.append(v)
                except Exception:
                    vals.append(None)
            return vals
    return []


def fetch_one(ticker: str) -> RawMetrics:
    _wait_for_cooldown()
    m = RawMetrics(ticker=ticker)
    yahoo_symbol = _yahoo_symbol(ticker)
    try:
        t = yf.Ticker(yahoo_symbol)
        info_error = None
        try:
            info = t.info or {}
        except Exception as exc:
            info = {}
            info_error = exc
            log.debug("%s: info endpoint unavailable (%s); trying fast fallback", ticker, exc)

        m.name = info.get("shortName") or info.get("longName")
        m.sector = info.get("sector")
        m.industry = info.get("industry")
        m.currency = info.get("currency")
        m.quote_type = info.get("quoteType")
        m.market_cap = _as_float(info.get("marketCap"))
        m.current_price = _as_float(_safe_get(info, "currentPrice", "regularMarketPrice", "previousClose"))
        if str(ticker).upper().endswith(".CC"):
            m.quote_type = "CRYPTO"
            m.currency = m.currency or "USD"
            m.name = m.name or str(ticker).upper().removesuffix(".CC")
        if not info or m.current_price is None:
            _apply_fast_fallback(t, m)
        # A failure of the heavy info endpoint is not fatal if fast_info/history
        # still gives a tradable identity/price. This is critical for portfolio
        # coverage under transient Yahoo throttling.
        if info_error is not None and m.current_price is None:
            raise info_error
        m.name = m.name or ticker
        raw_summary = info.get("longBusinessSummary")
        if raw_summary:
            # Card display needs a one-line blurb, not the full paragraph
            # yfinance returns (often 500-1000+ chars). Cut at the first
            # sentence if it's reasonably short; otherwise hard-truncate at
            # a word boundary near 160 chars.
            first_sentence = raw_summary.split(". ")[0].strip()
            if first_sentence and len(first_sentence) <= 180:
                m.business_summary = first_sentence + ("." if not first_sentence.endswith(".") else "")
            else:
                cut = raw_summary[:160].rsplit(" ", 1)[0]
                m.business_summary = cut + "…"

        # quality / profitability
        m.roe = _as_float(info.get("returnOnEquity"))
        m.roa = _as_float(info.get("returnOnAssets"))
        m.profit_margin = _as_float(info.get("profitMargins"))
        m.operating_margin = _as_float(info.get("operatingMargins"))
        m.gross_margin = _as_float(info.get("grossMargins"))

        # growth
        m.revenue_growth = _as_float(info.get("revenueGrowth"))
        m.earnings_growth = _as_float(info.get("earningsGrowth"))
        m.earnings_quarterly_growth = _as_float(info.get("earningsQuarterlyGrowth"))

        # cash flow
        m.free_cash_flow = _as_float(info.get("freeCashflow"))
        m.operating_cash_flow = _as_float(info.get("operatingCashflow"))

        # balance sheet
        m.current_ratio = _as_float(info.get("currentRatio"))
        m.quick_ratio = _as_float(info.get("quickRatio"))
        m.debt_to_equity = _as_float(info.get("debtToEquity"))
        m.total_cash = _as_float(info.get("totalCash"))
        m.total_debt = _as_float(info.get("totalDebt"))
        m.ebitda = _as_float(info.get("ebitda"))

        # valuation
        m.trailing_pe = _as_float(info.get("trailingPE"))
        m.forward_pe = _as_float(info.get("forwardPE"))
        m.price_to_book = _as_float(info.get("priceToBook"))
        m.enterprise_to_ebitda = _as_float(info.get("enterpriseToEbitda"))
        m.peg_ratio = _as_float(info.get("pegRatio"))

        # shareholder return / risk
        m.dividend_yield = _as_float(info.get("dividendYield"))
        m.payout_ratio = _as_float(info.get("payoutRatio"))
        m.beta = _as_float(info.get("beta"))

        if m.quote_type == "ETF":
            # Yahoo reports fund expense ratios in percentage points (e.g. 0.03 = 0.03%).
            m.expense_ratio = _as_float(_safe_get(info, "annualReportExpenseRatio", "netExpenseRatio"))
            m.fund_family = _safe_get(info, "fundFamily", "fundFamilyName")
            m.fund_category = _safe_get(info, "category", "fundCategory")
            m.fund_legal_type = info.get("legalType")
            m.fund_total_assets = _as_float(_safe_get(info, "totalAssets", "netAssets"))
            inception = info.get("fundInceptionDate")
            if inception is not None:
                try:
                    import datetime as _dt
                    m.fund_inception_date = _dt.datetime.utcfromtimestamp(float(inception)).date().isoformat()
                except Exception:
                    m.fund_inception_date = str(inception)
            try:
                funds_data = t.funds_data
                if funds_data is not None:
                    try:
                        m.fund_description = funds_data.description or None
                    except Exception:
                        pass
                    try:
                        overview = funds_data.fund_overview or {}
                        if isinstance(overview, dict):
                            m.fund_family = m.fund_family or overview.get("family") or overview.get("fundFamily")
                            m.fund_category = m.fund_category or overview.get("categoryName") or overview.get("category")
                            m.fund_legal_type = m.fund_legal_type or overview.get("legalType")
                    except Exception:
                        pass
                    try:
                        ac = funds_data.asset_classes or {}
                        if isinstance(ac, dict):
                            m.fund_asset_classes = {str(k): _as_float(v) for k,v in ac.items() if _as_float(v) is not None}
                    except Exception:
                        pass
                    try:
                        sw = funds_data.sector_weightings or {}
                        if isinstance(sw, dict):
                            m.fund_sector_weightings = {str(k): _as_float(v) for k,v in sw.items() if _as_float(v) is not None}
                    except Exception:
                        pass
                    try:
                        th = funds_data.top_holdings
                        if th is not None and not th.empty and "Holding Percent" in th.columns:
                            holdings=[]
                            for symbol, row in th.iterrows():
                                weight=_as_float(row.get("Holding Percent"))
                                if weight is None: continue
                                holdings.append({"symbol": str(symbol), "name": str(row.get("Name") or symbol), "weight": weight})
                            m.top_holdings = holdings
                    except Exception as e:
                        log.debug("%s: no top holdings data (%s)", ticker, e)
            except Exception as e:
                log.debug("%s: no funds data (%s)", ticker, e)
        else:
            # Quarterly trajectory: latest five quarters allow a like-for-like YoY
            # comparison (Q0 vs Q4) without pretending sequential seasonality is growth.
            try:
                qfin = t.quarterly_financials
                if qfin is not None and not qfin.empty:
                    cols = list(qfin.columns)[:6]

                    def series_for(labels):
                        for label in labels:
                            if label in qfin.index:
                                vals = []
                                for c in cols:
                                    v = _as_float(qfin.loc[label, c])
                                    vals.append({"date": str(getattr(c, "date", lambda: c)()), "value": v})
                                return vals
                        return []

                    m.quarterly_revenue = series_for(("Total Revenue", "Operating Revenue"))
                    m.quarterly_net_income = series_for(("Net Income", "Net Income Common Stockholders"))
                    m.quarterly_diluted_shares = series_for(("Diluted Average Shares", "Basic Average Shares"))
                    m.quarterly_eps = series_for(("Diluted EPS", "Basic EPS"))
                    m.quarterly_rnd = series_for(("Research And Development", "Research Development"))

                    def yoy_at(series, offset=0):
                        old = offset + 4
                        if len(series) > old and series[offset]["value"] is not None and series[old]["value"] not in (None, 0):
                            return series[offset]["value"] / series[old]["value"] - 1.0
                        return None

                    m.revenue_yoy_latest = yoy_at(m.quarterly_revenue, 0)
                    m.revenue_yoy_prior = yoy_at(m.quarterly_revenue, 1)
                    if m.revenue_yoy_latest is not None and m.revenue_yoy_prior is not None:
                        m.revenue_yoy_acceleration_pp = (m.revenue_yoy_latest - m.revenue_yoy_prior) * 100.0
                    m.net_income_yoy_latest = yoy_at(m.quarterly_net_income, 0)
                    m.net_income_yoy_prior = yoy_at(m.quarterly_net_income, 1)
                    if m.net_income_yoy_latest is not None and m.net_income_yoy_prior is not None:
                        m.net_income_yoy_acceleration_pp = (m.net_income_yoy_latest - m.net_income_yoy_prior) * 100.0
                    m.diluted_shares_yoy = yoy_at(m.quarterly_diluted_shares, 0)
                    m.eps_yoy_latest = yoy_at(m.quarterly_eps, 0)
                    m.eps_yoy_prior = yoy_at(m.quarterly_eps, 1)
                    if m.eps_yoy_latest is not None and m.eps_yoy_prior is not None:
                        m.eps_yoy_acceleration_pp = (m.eps_yoy_latest - m.eps_yoy_prior) * 100.0
                    m.rnd_yoy = yoy_at(m.quarterly_rnd, 0)
                    if m.quarterly_rnd and m.quarterly_rnd[0].get("value") is not None:
                        m.rnd_latest_quarter = abs(m.quarterly_rnd[0]["value"])
                        if m.quarterly_revenue and m.quarterly_revenue[0].get("value") not in (None, 0):
                            m.rnd_to_revenue = m.rnd_latest_quarter / abs(m.quarterly_revenue[0]["value"])

                    if m.quarterly_revenue and m.quarterly_net_income and m.quarterly_revenue[0]["value"] not in (None, 0) and m.quarterly_net_income[0]["value"] is not None:
                        m.net_margin_latest = m.quarterly_net_income[0]["value"] / m.quarterly_revenue[0]["value"]
                    if len(m.quarterly_revenue) >= 5 and len(m.quarterly_net_income) >= 5 and m.quarterly_revenue[4]["value"] not in (None, 0) and m.quarterly_net_income[4]["value"] is not None:
                        old_margin = m.quarterly_net_income[4]["value"] / m.quarterly_revenue[4]["value"]
                        if m.net_margin_latest is not None:
                            m.net_margin_yoy_change_pp = (m.net_margin_latest - old_margin) * 100.0
                    if (len(m.quarterly_revenue) >= 6 and len(m.quarterly_net_income) >= 6
                            and m.quarterly_revenue[1]["value"] not in (None, 0)
                            and m.quarterly_revenue[5]["value"] not in (None, 0)
                            and m.quarterly_net_income[1]["value"] is not None
                            and m.quarterly_net_income[5]["value"] is not None):
                        prev_margin = m.quarterly_net_income[1]["value"] / m.quarterly_revenue[1]["value"]
                        prev_old_margin = m.quarterly_net_income[5]["value"] / m.quarterly_revenue[5]["value"]
                        m.net_margin_yoy_change_prior_pp = (prev_margin - prev_old_margin) * 100.0
            except Exception as e:
                log.debug("%s: quarterly financials unavailable (%s)", ticker, e)

            # Latest quarterly repurchases are read from the cash-flow statement.
            # Yahoo commonly stores repurchases as a negative financing cash flow;
            # expose a positive absolute amount to the UI for readability.
            try:
                qcf = t.quarterly_cashflow
                if qcf is not None and not qcf.empty:
                    for label in ("Repurchase Of Capital Stock", "Repurchase Of Stock"):
                        if label in qcf.index:
                            v = _as_float(qcf.loc[label].iloc[0])
                            if v is not None:
                                m.repurchases_last_quarter = abs(v)
                            break
            except Exception as e:
                log.debug("%s: quarterly cashflow unavailable (%s)", ticker, e)

            # Interest coverage is derived from the latest income statement.
            try:
                fin = t.financials
                if fin is not None and not fin.empty:
                    for label in ("EBIT", "Operating Income"):
                        if label in fin.index:
                            m.ebit = _as_float(fin.loc[label].iloc[0])
                            break
                    for label in ("Interest Expense", "Interest Expense Non Operating"):
                        if label in fin.index:
                            val = _as_float(fin.loc[label].iloc[0])
                            m.interest_expense = abs(val) if val is not None else None
                            break
            except Exception as e:
                log.debug("%s: financials unavailable (%s)", ticker, e)

            # Balance-sheet anchors and capital-efficiency proxy. Keeping total
            # assets/equity for every company lets the scoring layer calculate
            # accrual quality without fabricating missing accounting data.
            try:
                bs = t.balance_sheet
                if bs is not None and not bs.empty:
                    total_assets = _row_value(bs, ("Total Assets",))
                    equity = _row_value(bs, ("Stockholders Equity", "Total Stockholder Equity", "Common Stock Equity", "Total Equity Gross Minority Interest"))
                    if m.total_assets is None:
                        m.total_assets = total_assets
                    if m.stockholders_equity is None:
                        m.stockholders_equity = equity
                    if m.ebit is not None:
                        current_liab = _row_value(bs, ("Current Liabilities", "Total Current Liabilities"))
                        capital_employed = None
                        if total_assets is not None and current_liab is not None:
                            capital_employed = total_assets - current_liab
                        if capital_employed not in (None, 0) and capital_employed > 0:
                            m.roce_proxy = m.ebit / capital_employed
            except Exception as e:
                log.debug("%s: balance-sheet anchors/ROCE proxy unavailable (%s)", ticker, e)

            # Annual quality context for Winston-style "current / 1Y / 3Y" cards.
            # These are statement-derived historical observations, not estimates.
            try:
                fin = t.financials
                bs = t.balance_sheet
                if fin is not None and not fin.empty:
                    cols = list(fin.columns)[:4]
                    def row_at(frame, labels, col):
                        if frame is None or frame.empty:
                            return None
                        for label in labels:
                            if label in frame.index and col in frame.columns:
                                return _as_float(frame.loc[label, col])
                        return None
                    hist=[]
                    for c in cols:
                        revenue=row_at(fin,("Total Revenue","Operating Revenue"),c)
                        gross=row_at(fin,("Gross Profit",),c)
                        op=row_at(fin,("Operating Income","EBIT"),c)
                        net=row_at(fin,("Net Income","Net Income Common Stockholders"),c)
                        ebit=row_at(fin,("EBIT","Operating Income"),c)
                        assets=row_at(bs,("Total Assets",),c) if bs is not None else None
                        equity=row_at(bs,("Stockholders Equity","Total Stockholder Equity","Common Stock Equity"),c) if bs is not None else None
                        cur_liab=row_at(bs,("Current Liabilities","Total Current Liabilities"),c) if bs is not None else None
                        item={"date": str(getattr(c,"date",lambda:c)())}
                        if revenue not in (None,0):
                            if gross is not None: item["gross_margin"]=gross/revenue
                            if op is not None: item["operating_margin"]=op/revenue
                            if net is not None: item["net_margin"]=net/revenue
                        if equity not in (None,0) and net is not None:
                            item["roe"]=net/equity
                        if assets is not None and cur_liab is not None and ebit is not None and (assets-cur_liab)>0:
                            item["roce_proxy"]=ebit/(assets-cur_liab)
                        if len(item)>1: hist.append(item)
                    m.annual_quality_history=hist
            except Exception as e:
                log.debug("%s: annual quality history unavailable (%s)", ticker, e)

            # Dividend-per-share history from actual Yahoo dividend events.
            try:
                div=t.dividends
                if div is not None and len(div):
                    by_year={}
                    for idx,val in div.items():
                        yr=str(getattr(idx,"year", ""))
                        v=_as_float(val)
                        if yr and v is not None:
                            by_year[yr]=by_year.get(yr,0.0)+v
                    m.annual_dividend_history=[{"year":y,"value":round(by_year[y],8)} for y in sorted(by_year, reverse=True)[:4]]
            except Exception as e:
                log.debug("%s: dividend history unavailable (%s)", ticker, e)

            # Dividend safety proxy: annual FCF divided by the market-implied
            # annual dividend cash requirement. Only emitted when both sides are
            # positive and available; missing data remain missing.
            try:
                if (m.free_cash_flow is not None and m.free_cash_flow > 0 and
                        m.market_cap and m.market_cap > 0 and m.dividend_yield and m.dividend_yield > 0):
                    implied_dividends = m.market_cap * m.dividend_yield
                    if implied_dividends > 0:
                        m.dividend_fcf_coverage = m.free_cash_flow / implied_dividends
            except Exception:
                pass

            # Bank-native proxies from public financial statements. These are
            # intentionally labelled proxies: CET1 and NPL ratios require
            # regulatory filings and are NOT inferred from generic statements.
            sector = (m.sector or "").lower()
            industry = (m.industry or "").lower()
            is_bank = "financial" in sector and any(k in industry for k in ("bank", "credit", "savings", "thrift"))
            if is_bank:
                try:
                    qfin = t.quarterly_financials
                    fin = t.financials
                    bs = t.balance_sheet

                    nii_series = _row_series(qfin, ("Net Interest Income", "Net Interest Income After Provision"), 6)
                    if nii_series:
                        m.net_interest_income = nii_series[0]
                        if len(nii_series) >= 5 and nii_series[0] is not None and nii_series[4] not in (None, 0):
                            m.net_interest_income_yoy = nii_series[0] / nii_series[4] - 1.0

                    latest_revenue = _row_value(fin, ("Total Revenue", "Operating Revenue"))
                    latest_opex = _row_value(fin, ("Operating Expense", "Total Operating Expenses", "Non Interest Expense"))
                    if latest_revenue not in (None, 0) and latest_opex is not None:
                        m.efficiency_ratio_proxy = abs(latest_opex) / abs(latest_revenue)

                    provision = _row_value(fin, ("Provision For Loan Losses", "Provision for Credit Losses", "Credit Losses Provision"))
                    if provision is not None:
                        m.provision_for_credit_losses = abs(provision)
                        if latest_revenue not in (None, 0):
                            m.provision_to_revenue = abs(provision) / abs(latest_revenue)

                    m.total_assets = _row_value(bs, ("Total Assets",))
                    m.stockholders_equity = _row_value(bs, ("Stockholders Equity", "Total Equity Gross Minority Interest", "Common Stock Equity"))
                    if m.total_assets not in (None, 0) and m.stockholders_equity is not None:
                        m.equity_to_assets = m.stockholders_equity / m.total_assets

                    bank_vals = [m.net_interest_income, m.net_interest_income_yoy, m.efficiency_ratio_proxy,
                                 m.provision_to_revenue, m.equity_to_assets]
                    m.bank_metric_coverage_pct = sum(v is not None for v in bank_vals) / len(bank_vals) * 100.0
                except Exception as e:
                    log.debug("%s: bank proxy metrics unavailable (%s)", ticker, e)

            # Insurance-native public-statement proxies. Generic Yahoo statements
            # vary materially between life, P&C and reinsurance businesses, so
            # these are intentionally conservative and never presented as
            # regulatory solvency ratios or as a reported combined ratio.
            is_insurance = "financial" in sector and any(k in industry for k in ("insurance", "insur"))
            if is_insurance:
                try:
                    fin = t.financials
                    bs = t.balance_sheet

                    latest_revenue = _row_value(fin, ("Total Revenue", "Operating Revenue"))
                    m.insurance_net_investment_income = _row_value(fin, (
                        "Net Investment Income", "Investment Income", "Net Investment Income Net"
                    ))
                    claims = _row_value(fin, (
                        "Policyholder Benefits", "Policyholder Benefits And Claims Payable",
                        "Losses And Loss Adjustment Expenses", "Loss And Loss Adjustment Expense",
                        "Insurance And Claims"
                    ))
                    if claims is not None:
                        m.insurance_claims_benefits = abs(claims)
                        if latest_revenue not in (None, 0):
                            m.insurance_claims_to_revenue = abs(claims) / abs(latest_revenue)

                    opex = _row_value(fin, (
                        "Operating Expense", "Total Operating Expenses",
                        "Selling General And Administration", "General And Administrative Expense"
                    ))
                    if opex is not None:
                        m.insurance_operating_expense = abs(opex)
                    # This ratio is a broad cost-load proxy only. It is NOT a
                    # statutory combined ratio because generic statements do not
                    # reliably separate earned premium, claims and acquisition costs.
                    if latest_revenue not in (None, 0) and claims is not None and opex is not None:
                        m.insurance_operating_ratio_proxy = (abs(claims) + abs(opex)) / abs(latest_revenue)

                    total_assets = _row_value(bs, ("Total Assets",))
                    equity = _row_value(bs, (
                        "Stockholders Equity", "Total Equity Gross Minority Interest", "Common Stock Equity"
                    ))
                    if total_assets not in (None, 0) and equity is not None:
                        m.insurance_equity_to_assets = equity / total_assets

                    diluted = _row_value(fin, ("Diluted Average Shares", "Basic Average Shares"))
                    if equity is not None and diluted not in (None, 0):
                        m.insurance_book_value_per_share_proxy = equity / diluted

                    ins_vals = [
                        m.insurance_net_investment_income, m.insurance_claims_to_revenue,
                        m.insurance_operating_ratio_proxy, m.insurance_book_value_per_share_proxy,
                        m.insurance_equity_to_assets,
                    ]
                    m.insurance_metric_coverage_pct = sum(v is not None for v in ins_vals) / len(ins_vals) * 100.0
                except Exception as e:
                    log.debug("%s: insurance proxy metrics unavailable (%s)", ticker, e)

            # REIT-native public-statement proxies. NAREIT FFO requires net income
            # adjusted for real-estate depreciation/amortisation and gains/losses
            # on property sales. Yahoo does not consistently expose every
            # component, so this remains explicitly labelled an FFO proxy. AFFO,
            # NAV and occupancy are not inferred.
            is_reit = "real estate" in sector or "reit" in industry
            if is_reit:
                try:
                    fin = t.financials
                    cf = t.cashflow
                    net_income = _row_value(fin, ("Net Income", "Net Income Common Stockholders"))
                    dep_amort = _row_value(cf, (
                        "Depreciation And Amortization",
                        "Depreciation Amortization Depletion",
                        "Depreciation",
                    ))
                    sale_adj = _row_value(cf, (
                        "Gain Loss On Sale Of PPE",
                        "Gain Loss On Sale Of Property Plant Equipment",
                        "Gain Loss On Sale Of Assets",
                    ))
                    m.reit_depreciation_amortization = abs(dep_amort) if dep_amort is not None else None
                    m.reit_gain_loss_sale_adjustment = sale_adj
                    if net_income is not None and dep_amort is not None:
                        # Cash-flow reconciliation normally reports gains as a
                        # negative adjustment and losses as positive, matching
                        # the FFO add-back/subtraction direction.
                        m.reit_ffo_proxy = net_income + abs(dep_amort) + (sale_adj or 0.0)

                    diluted = _row_value(fin, ("Diluted Average Shares", "Basic Average Shares"))
                    if m.reit_ffo_proxy is not None and diluted not in (None, 0):
                        m.reit_ffo_per_share_proxy = m.reit_ffo_proxy / diluted
                        if m.current_price is not None and m.reit_ffo_per_share_proxy > 0:
                            m.reit_p_ffo_proxy = m.current_price / m.reit_ffo_per_share_proxy

                    dividends_paid = _row_value(cf, ("Cash Dividends Paid", "Common Stock Dividend Paid"))
                    if m.reit_ffo_proxy not in (None, 0) and dividends_paid is not None and m.reit_ffo_proxy > 0:
                        m.reit_ffo_payout_proxy = abs(dividends_paid) / m.reit_ffo_proxy

                    if m.ebitda not in (None, 0) and m.ebitda > 0 and (m.total_debt is not None or m.total_cash is not None):
                        net_debt = (m.total_debt or 0.0) - (m.total_cash or 0.0)
                        m.reit_net_debt_to_ebitda = net_debt / m.ebitda

                    reit_vals = [m.reit_ffo_proxy, m.reit_p_ffo_proxy, m.reit_ffo_payout_proxy,
                                 m.reit_net_debt_to_ebitda, m.dividend_yield]
                    m.reit_metric_coverage_pct = sum(v is not None for v in reit_vals) / len(reit_vals) * 100.0
                except Exception as e:
                    log.debug("%s: REIT proxy metrics unavailable (%s)", ticker, e)

    except Exception as e:
        m.error = str(e)
        if _is_rate_limit_error(e):
            _register_rate_limit_hit()
        log.warning("%s: fetch failed (%s)", ticker, e)

    return m


# Shared, thread-safe rate-limit cooldown. Root cause found in a real run's
# log: yfinance raises YFRateLimitError near-instantly and in bulk once
# Yahoo's per-IP limit trips (hundreds of tickers failing within the same
# second) — the old code treated each failure as independent and kept
# hammering at full concurrency, which both wastes the run (most of the
# universe silently drops out) and likely deepens whatever penalty Yahoo
# is applying. Any worker that sees a rate-limit error now sets a shared
# "resume no earlier than" timestamp with escalating backoff; every worker
# checks it before each request and sleeps if still in cooldown, so the
# whole pool backs off together instead of independently retrying into
# the same wall.
_cooldown_lock = threading.Lock()
_cooldown_until = 0.0
_cooldown_strikes = 0


def _is_rate_limit_error(exc: Exception) -> bool:
    name = type(exc).__name__
    msg = str(exc)
    return "RateLimit" in name or "Too Many Requests" in msg or "rate limit" in msg.lower()


def _wait_for_cooldown():
    with _cooldown_lock:
        remaining = _cooldown_until - time.time()
    if remaining > 0:
        time.sleep(remaining)


def _register_rate_limit_hit():
    global _cooldown_until, _cooldown_strikes
    with _cooldown_lock:
        _cooldown_strikes += 1
        # Escalating cooldown: 20s, 40s, 80s, ... capped at 5 minutes so a
        # very long block doesn't eat the whole Actions run budget either.
        backoff = min(300, 20 * (2 ** (_cooldown_strikes - 1)))
        candidate = time.time() + backoff
        if candidate > _cooldown_until:
            _cooldown_until = candidate
            log.warning("Yahoo rate-limit detected — pausing all fetch workers for %ds (strike %d)", backoff, _cooldown_strikes)


def fetch_many(tickers: list[str], pause: float = 0.0, workers_override: int | None = None, retries: int = 3) -> list[RawMetrics]:
    """Fetch fundamentals concurrently but conservatively.

    Portfolio coverage expanded the universe materially; the old sequential loop
    could take longer than the GitHub Action budget and left the UI on an old
    stocks.json even though newer front-end releases were deployed. A small
    worker pool keeps Yahoo request pressure bounded while making a full refresh
    practical. Failed rows are retried after the parallel pass, with the shared
    cooldown (see _wait_for_cooldown) making later retry passes actually wait
    out a rate-limit window instead of immediately reproducing it.
    """
    tickers = list(dict.fromkeys(tickers))
    if not tickers:
        return []
    workers = max(1, min(4, int(workers_override if workers_override is not None else os.getenv("FINSCANNER_FETCH_WORKERS", "4"))))
    results_by_ticker: dict[str, RawMetrics] = {}
    completed = 0
    log.info("Fetching %d tickers with %d workers", len(tickers), workers)
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="yf") as pool:
        future_map = {pool.submit(fetch_one, tk): tk for tk in tickers}
        for fut in as_completed(future_map):
            tk = future_map[fut]
            try:
                results_by_ticker[tk] = fut.result()
            except Exception as exc:
                log.warning("%s: worker failed (%s)", tk, exc)
                results_by_ticker[tk] = RawMetrics(ticker=tk, error=str(exc))
            completed += 1
            if completed % 50 == 0 or completed == len(tickers):
                log.info("fetched %d/%d", completed, len(tickers))

    for attempt in range(max(0, int(retries))):
        failed = [tk for tk in tickers if getattr(results_by_ticker.get(tk), "error", None)]
        if not failed:
            break
        # Exponential backoff between retry passes (not just the per-worker
        # cooldown above) — a pass that hit a rate-limit wall needs more
        # than a couple seconds before trying the same tickers again.
        backoff = min(120, 8 * (2 ** attempt))
        log.info("Retrying %d failed ticker(s), pass %d/%d (waiting %ds first)", len(failed), attempt + 1, retries, backoff)
        time.sleep(backoff)
        # Retry sequentially: after a Yahoo throttle event, another burst of
        # parallel requests tends to reproduce the same failure.
        for i, tk in enumerate(failed):
            retry = fetch_one(tk)
            if not getattr(retry, "error", None):
                results_by_ticker[tk] = retry
            if pause:
                time.sleep(pause)
            if (i + 1) % 50 == 0:
                log.info("retry pass %d: %d/%d", attempt + 1, i + 1, len(failed))

    still_failed = sum(1 for tk in tickers if getattr(results_by_ticker.get(tk), "error", None))
    if still_failed:
        log.warning("%d/%d tickers still failed after all retries — likely a sustained Yahoo rate-limit or genuinely delisted/invalid tickers", still_failed, len(tickers))

    return [results_by_ticker[tk] for tk in tickers if tk in results_by_ticker]
