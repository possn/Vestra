"""Targeted fundamental gap retrieval for sparse equity dossiers.

Runs only after primary Yahoo + SEC/ESEF enrichment and only for equities that
still miss a material share of critical metrics. It uses Yahoo statement tables
(income statement, balance sheet and cash-flow statement) rather than the heavy
`info` endpoint, and fills only missing fields. No value is fabricated: if a
required statement line or denominator is unavailable the metric remains None.
"""
from __future__ import annotations

import logging
import time
import yfinance as yf

log = logging.getLogger("gap_retrieval")

CRITICAL = (
    "roe","roa","profit_margin","operating_margin","gross_margin",
    "revenue_growth","earnings_growth","free_cash_flow","operating_cash_flow",
    "current_ratio","quick_ratio","debt_to_equity","trailing_pe","forward_pe",
    "enterprise_to_ebitda","price_to_book","roce_proxy",
)


def _f(v):
    try:
        x=float(v)
        return x if x==x and abs(x)!=float("inf") else None
    except (TypeError, ValueError):
        return None


def _coverage(m):
    return sum(getattr(m,k,None) is not None for k in CRITICAL)/len(CRITICAL)*100.0


def _frame(t, name):
    try:
        x=getattr(t,name)
        return x if x is not None and not getattr(x,"empty",True) else None
    except Exception:
        return None


def _value(frame, labels, col=0):
    if frame is None: return None
    for label in labels:
        if label in frame.index:
            try: return _f(frame.loc[label].iloc[col])
            except Exception: pass
    return None


def _series(frame, labels, limit=4):
    if frame is None: return []
    for label in labels:
        if label in frame.index:
            out=[]
            for c in list(frame.columns)[:limit]:
                try: out.append(_f(frame.loc[label,c]))
                except Exception: out.append(None)
            return out
    return []


def _growth(vals):
    if len(vals)<2 or vals[0] is None or vals[1] in (None,0): return None
    return vals[0]/vals[1]-1.0


def _set_missing(m,key,value):
    if value is not None and getattr(m,key,None) is None:
        setattr(m,key,value)
        return True
    return False


def _yahoo_symbol(ticker):
    t=str(ticker or "").strip().upper()
    return t[:-3]+"-USD" if t.endswith(".CC") else t


def enrich(raw, priority=None, max_rows=220, threshold=68.0):
    """Deep-fill only sparse equity rows.

    Priority holdings are attempted first. Non-priority rows are processed only
    while critical coverage is below `threshold`, keeping requests bounded.
    """
    priority=set(priority or [])
    candidates=[]
    for m in raw:
        if getattr(m,"quote_type",None) in ("ETF","CRYPTO") or getattr(m,"error",None):
            continue
        cov=_coverage(m)
        if cov < threshold or str(getattr(m,"ticker","") or "").upper() in priority:
            candidates.append((0 if str(getattr(m,"ticker","") or "").upper() in priority else 1,cov,m))
    candidates.sort(key=lambda x:(x[0],x[1]))

    attempted=filled=0
    for _,before,m in candidates[:max_rows]:
        ticker=str(getattr(m,"ticker","") or "").upper()
        if not ticker: continue
        attempted+=1
        try:
            t=yf.Ticker(_yahoo_symbol(ticker))
            inc=_frame(t,"income_stmt")
            bal=_frame(t,"balance_sheet")
            cf=_frame(t,"cashflow")
            if inc is None and bal is None and cf is None:
                continue

            revenue=_value(inc,("Total Revenue","Operating Revenue","Revenue"))
            net_income=_value(inc,("Net Income","Net Income Common Stockholders","Net Income Including Noncontrolling Interests"))
            op_income=_value(inc,("Operating Income","EBIT"))
            gross_profit=_value(inc,("Gross Profit",))
            ebit=_value(inc,("EBIT","Operating Income"))
            interest=_value(inc,("Interest Expense","Interest Expense Non Operating"))
            ebitda=_value(inc,("EBITDA","Normalized EBITDA"))

            assets=_value(bal,("Total Assets",))
            equity=_value(bal,("Stockholders Equity","Total Equity Gross Minority Interest","Common Stock Equity"))
            current_assets=_value(bal,("Current Assets","Total Current Assets"))
            current_liab=_value(bal,("Current Liabilities","Total Current Liabilities"))
            cash=_value(bal,("Cash Cash Equivalents And Short Term Investments","Cash And Cash Equivalents","Cash Financial"))
            receivables=_value(bal,("Receivables","Accounts Receivable","Net Receivables"))
            debt=_value(bal,("Total Debt",))
            if debt is None:
                current_debt=_value(bal,("Current Debt","Current Debt And Capital Lease Obligation"))
                long_debt=_value(bal,("Long Term Debt","Long Term Debt And Capital Lease Obligation"))
                if current_debt is not None or long_debt is not None:
                    debt=(current_debt or 0)+(long_debt or 0)

            cfo=_value(cf,("Operating Cash Flow","Total Cash From Operating Activities"))
            capex=_value(cf,("Capital Expenditure","Capital Expenditures","Purchase Of PPE"))
            fcf=_value(cf,("Free Cash Flow",))
            if fcf is None and cfo is not None and capex is not None:
                fcf=cfo-abs(capex)

            changed=False
            if revenue not in (None,0):
                if gross_profit is not None: changed |= _set_missing(m,"gross_margin",gross_profit/revenue)
                if op_income is not None: changed |= _set_missing(m,"operating_margin",op_income/revenue)
                if net_income is not None: changed |= _set_missing(m,"profit_margin",net_income/revenue)
            if equity not in (None,0) and net_income is not None: changed |= _set_missing(m,"roe",net_income/equity)
            if assets not in (None,0) and net_income is not None: changed |= _set_missing(m,"roa",net_income/assets)
            if current_liab not in (None,0):
                if current_assets is not None: changed |= _set_missing(m,"current_ratio",current_assets/current_liab)
                if cash is not None or receivables is not None: changed |= _set_missing(m,"quick_ratio",((cash or 0)+(receivables or 0))/current_liab)
            if equity not in (None,0) and debt is not None: changed |= _set_missing(m,"debt_to_equity",debt/equity)
            changed |= _set_missing(m,"total_cash",cash)
            changed |= _set_missing(m,"total_debt",debt)
            changed |= _set_missing(m,"operating_cash_flow",cfo)
            changed |= _set_missing(m,"free_cash_flow",fcf)
            changed |= _set_missing(m,"ebit",ebit)
            changed |= _set_missing(m,"interest_expense",abs(interest) if interest is not None else None)
            changed |= _set_missing(m,"ebitda",ebitda)

            revs=_series(inc,("Total Revenue","Operating Revenue","Revenue"),4)
            nis=_series(inc,("Net Income","Net Income Common Stockholders","Net Income Including Noncontrolling Interests"),4)
            changed |= _set_missing(m,"revenue_growth",_growth(revs))
            changed |= _set_missing(m,"earnings_growth",_growth(nis))

            # ROCE proxy = EBIT / (equity + debt - cash), only when all required
            # balance-sheet components exist and invested capital is positive.
            if ebit is not None and equity is not None and debt is not None and cash is not None:
                invested=equity+debt-cash
                if invested>0: changed |= _set_missing(m,"roce_proxy",ebit/invested)

            # Statement-derived valuation fallbacks are allowed only when the
            # denominator is positive and the market numerator is observed.
            price=_f(getattr(m,"current_price",None)); cap=_f(getattr(m,"market_cap",None))
            shares=_value(inc,("Diluted Average Shares","Basic Average Shares"))
            eps=_value(inc,("Diluted EPS","Basic EPS"))
            if price and eps and eps>0: changed |= _set_missing(m,"trailing_pe",price/eps)
            if price and shares and shares>0 and equity and equity>0: changed |= _set_missing(m,"price_to_book",price/(equity/shares))
            if cap and ebitda and ebitda>0:
                ev=cap+(debt or 0)-(cash or 0)
                if ev>0: changed |= _set_missing(m,"enterprise_to_ebitda",ev/ebitda)

            hist=[]
            years=min(4,max(len(revs),len(nis)))
            eqs=_series(bal,("Stockholders Equity","Total Equity Gross Minority Interest","Common Stock Equity"),4)
            assets_s=_series(bal,("Total Assets",),4)
            ops=_series(inc,("Operating Income","EBIT"),4)
            gps=_series(inc,("Gross Profit",),4)
            for i in range(years):
                rev=revs[i] if i<len(revs) else None; ni=nis[i] if i<len(nis) else None
                eq=eqs[i] if i<len(eqs) else None; ass=assets_s[i] if i<len(assets_s) else None
                op=ops[i] if i<len(ops) else None; gp=gps[i] if i<len(gps) else None
                hist.append({
                    "period_index":i,
                    "roe": ni/eq if ni is not None and eq not in (None,0) else None,
                    "roa": ni/ass if ni is not None and ass not in (None,0) else None,
                    "net_margin": ni/rev if ni is not None and rev not in (None,0) else None,
                    "operating_margin": op/rev if op is not None and rev not in (None,0) else None,
                    "gross_margin": gp/rev if gp is not None and rev not in (None,0) else None,
                })
            if hist and not getattr(m,"annual_quality_history",None):
                m.annual_quality_history=hist
                changed=True

            if changed:
                setattr(m,"gap_statement_enriched",True)
                setattr(m,"gap_coverage_before",round(before,1))
                setattr(m,"gap_coverage_after",round(_coverage(m),1))
                filled+=1
            time.sleep(0.05)
        except Exception as exc:
            log.debug("Gap retrieval %s: %s",ticker,exc)

    log.info("Targeted gap retrieval: attempted %d, enriched %d",attempted,filled)
    return raw
