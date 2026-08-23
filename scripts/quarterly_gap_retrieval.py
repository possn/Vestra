"""Quarterly/TTM fallback for sparse equity dossiers.

Runs after the annual statement gap retriever.  It uses Yahoo quarterly income,
balance-sheet and cash-flow tables to reconstruct only metrics that remain
missing.  It never replaces an observed value and never treats a missing line as
zero.  TTM metrics require at least three usable quarters; growth requires a
comparable prior-year quarter.
"""
from __future__ import annotations

import logging
import time
import yfinance as yf

log = logging.getLogger("quarterly_gap")

CRITICAL = (
    "roe", "roa", "profit_margin", "operating_margin", "gross_margin",
    "revenue_growth", "earnings_growth", "free_cash_flow", "operating_cash_flow",
    "current_ratio", "quick_ratio", "debt_to_equity", "roce_proxy",
)


def _f(v):
    try:
        x = float(v)
        return x if x == x and abs(x) != float("inf") else None
    except (TypeError, ValueError):
        return None


def _coverage(m):
    return sum(getattr(m, k, None) is not None for k in CRITICAL) / len(CRITICAL) * 100.0


def _frame(t, name):
    try:
        x = getattr(t, name)
        return x if x is not None and not getattr(x, "empty", True) else None
    except Exception:
        return None


def _row(frame, labels, limit=8):
    if frame is None:
        return []
    for label in labels:
        if label in frame.index:
            vals = []
            for c in list(frame.columns)[:limit]:
                try:
                    vals.append(_f(frame.loc[label, c]))
                except Exception:
                    vals.append(None)
            return vals
    return []


def _latest(vals):
    return next((v for v in vals if v is not None), None)


def _sum_recent(vals, n=4, minimum=3):
    usable = [v for v in vals[:n] if v is not None]
    if len(usable) < minimum:
        return None
    return sum(usable)


def _yoy(vals):
    # Yahoo quarterly tables are normally newest-first. Compare latest with the
    # quarter roughly one year earlier only when both observations exist.
    if len(vals) < 5 or vals[0] is None or vals[4] in (None, 0):
        return None
    return vals[0] / vals[4] - 1.0


def _set_missing(m, key, value):
    if value is not None and getattr(m, key, None) is None:
        setattr(m, key, value)
        return True
    return False


def _symbol(ticker):
    t = str(ticker or "").strip().upper()
    return t[:-3] + "-USD" if t.endswith(".CC") else t


def enrich(raw, priority=None, max_rows=180, threshold=65.0):
    priority = {str(x or "").upper() for x in (priority or [])}
    candidates = []
    for m in raw:
        if getattr(m, "quote_type", None) in ("ETF", "CRYPTO") or getattr(m, "error", None):
            continue
        ticker = str(getattr(m, "ticker", "") or "").upper()
        cov = _coverage(m)
        if cov < threshold or ticker in priority:
            candidates.append((0 if ticker in priority else 1, cov, m))
    candidates.sort(key=lambda x: (x[0], x[1]))

    attempted = enriched = 0
    for _, before, m in candidates[:max_rows]:
        ticker = str(getattr(m, "ticker", "") or "").upper()
        if not ticker:
            continue
        attempted += 1
        try:
            t = yf.Ticker(_symbol(ticker))
            inc = _frame(t, "quarterly_income_stmt")
            bal = _frame(t, "quarterly_balance_sheet")
            cf = _frame(t, "quarterly_cashflow")
            if inc is None and bal is None and cf is None:
                continue

            revs = _row(inc, ("Total Revenue", "Operating Revenue", "Revenue"))
            nis = _row(inc, ("Net Income", "Net Income Common Stockholders", "Net Income Including Noncontrolling Interests"))
            ops = _row(inc, ("Operating Income", "EBIT"))
            gps = _row(inc, ("Gross Profit",))
            ebits = _row(inc, ("EBIT", "Operating Income"))

            assets_s = _row(bal, ("Total Assets",))
            equity_s = _row(bal, ("Stockholders Equity", "Common Stock Equity", "Total Equity Gross Minority Interest"))
            ca_s = _row(bal, ("Current Assets", "Total Current Assets"))
            cl_s = _row(bal, ("Current Liabilities", "Total Current Liabilities"))
            cash_s = _row(bal, ("Cash Cash Equivalents And Short Term Investments", "Cash And Cash Equivalents", "Cash Financial"))
            recv_s = _row(bal, ("Receivables", "Accounts Receivable", "Net Receivables"))
            debt_s = _row(bal, ("Total Debt",))

            cfo_s = _row(cf, ("Operating Cash Flow", "Total Cash From Operating Activities"))
            capex_s = _row(cf, ("Capital Expenditure", "Capital Expenditures", "Purchase Of PPE"))
            fcf_s = _row(cf, ("Free Cash Flow",))

            rev_ttm = _sum_recent(revs)
            ni_ttm = _sum_recent(nis)
            op_ttm = _sum_recent(ops)
            gp_ttm = _sum_recent(gps)
            ebit_ttm = _sum_recent(ebits)
            cfo_ttm = _sum_recent(cfo_s)
            capex_ttm = _sum_recent(capex_s)
            fcf_ttm = _sum_recent(fcf_s)
            if fcf_ttm is None and cfo_ttm is not None and capex_ttm is not None:
                fcf_ttm = cfo_ttm - abs(capex_ttm)

            assets = _latest(assets_s)
            equity = _latest(equity_s)
            current_assets = _latest(ca_s)
            current_liab = _latest(cl_s)
            cash = _latest(cash_s)
            receivables = _latest(recv_s)
            debt = _latest(debt_s)

            changed = False
            if rev_ttm not in (None, 0):
                if ni_ttm is not None:
                    changed |= _set_missing(m, "profit_margin", ni_ttm / rev_ttm)
                if op_ttm is not None:
                    changed |= _set_missing(m, "operating_margin", op_ttm / rev_ttm)
                if gp_ttm is not None:
                    changed |= _set_missing(m, "gross_margin", gp_ttm / rev_ttm)
            if equity not in (None, 0) and ni_ttm is not None:
                changed |= _set_missing(m, "roe", ni_ttm / equity)
            if assets not in (None, 0) and ni_ttm is not None:
                changed |= _set_missing(m, "roa", ni_ttm / assets)
            if current_liab not in (None, 0):
                if current_assets is not None:
                    changed |= _set_missing(m, "current_ratio", current_assets / current_liab)
                if cash is not None or receivables is not None:
                    changed |= _set_missing(m, "quick_ratio", ((cash or 0) + (receivables or 0)) / current_liab)
            if equity not in (None, 0) and debt is not None:
                changed |= _set_missing(m, "debt_to_equity", debt / equity)

            changed |= _set_missing(m, "operating_cash_flow", cfo_ttm)
            changed |= _set_missing(m, "free_cash_flow", fcf_ttm)
            changed |= _set_missing(m, "revenue_growth", _yoy(revs))
            changed |= _set_missing(m, "earnings_growth", _yoy(nis))

            if ebit_ttm is not None and equity is not None and debt is not None and cash is not None:
                invested = equity + debt - cash
                if invested > 0:
                    changed |= _set_missing(m, "roce_proxy", ebit_ttm / invested)

            if changed:
                setattr(m, "quarterly_gap_enriched", True)
                setattr(m, "quarterly_gap_coverage_before", round(before, 1))
                setattr(m, "quarterly_gap_coverage_after", round(_coverage(m), 1))
                enriched += 1
            time.sleep(0.04)
        except Exception as exc:
            log.debug("Quarterly gap %s: %s", ticker, exc)

    log.info("Quarterly gap retrieval: attempted %d, enriched %d", attempted, enriched)
    return raw
