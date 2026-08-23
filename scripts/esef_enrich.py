"""European ESEF/UKSEF enrichment with strict identity resolution.

Identity chain:
  Yahoo ticker -> ISIN (yfinance) -> LEI (GLEIF/ANNA certified mapping)
  -> latest filing for that LEI (filings.xbrl.org) -> xBRL-JSON facts.

No issuer-name fuzzy matching is used. The enricher only fills metrics that are
missing in the primary Yahoo feed. If any identity hop is ambiguous, the row is
left unchanged.

v4.12 broadens the IFRS taxonomy fallback materially. Sparse European dossiers
were often caused by relying on only one canonical IFRS concept per metric while
issuers legitimately use alternative standard concepts. This module now derives
more profitability, liquidity, leverage, cash-flow and multi-year quality fields
without inventing values or using fuzzy issuer matching.
"""
from __future__ import annotations

import datetime as _dt
import logging
import re
import time
from urllib.parse import urljoin

import requests
import yfinance as yf

log = logging.getLogger("esef_enrich")

GLEIF = "https://api.gleif.org/api/v1/lei-records"
ESEF = "https://filings.xbrl.org"
USER_AGENT = "Vestra/4.0 (+https://github.com/possn/Vestra)"

_SUFFIX_COUNTRY = {
    ".L": "GB", ".PA": "FR", ".AS": "NL", ".BR": "BE", ".MC": "ES",
    ".MI": "IT", ".ST": "SE", ".HE": "FI", ".CO": "DK", ".OL": "NO",
    ".LS": "PT", ".VI": "AT", ".WA": "PL", ".PR": "CZ", ".AT": "GR",
    ".DE": "DE", ".SW": "CH",
}
_ISIN_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")

# Only standard IFRS concepts are accepted here. Extension concepts are not
# guessed because issuer-specific labels can mean different things.
_CONCEPTS = {
    "revenue": (
        "ifrs-full:Revenue",
        "ifrs-full:RevenueFromContractsWithCustomers",
        "ifrs-full:RevenueFromContractsWithCustomersExcludingAssessedTax",
    ),
    "net_income": (
        "ifrs-full:ProfitLoss",
        "ifrs-full:ProfitLossAttributableToOwnersOfParent",
    ),
    "operating_income": (
        "ifrs-full:ProfitLossFromOperatingActivities",
        "ifrs-full:OperatingProfitLoss",
    ),
    "gross_profit": ("ifrs-full:GrossProfit",),
    "assets": ("ifrs-full:Assets",),
    "assets_current": ("ifrs-full:CurrentAssets",),
    "liabilities_current": ("ifrs-full:CurrentLiabilities",),
    "equity": (
        "ifrs-full:Equity",
        "ifrs-full:EquityAttributableToOwnersOfParent",
    ),
    "cash": (
        "ifrs-full:CashAndCashEquivalents",
        "ifrs-full:CashAndCashEquivalentsAtCarryingValue",
    ),
    "inventory": ("ifrs-full:Inventories",),
    "cfo": (
        "ifrs-full:CashFlowsFromUsedInOperatingActivities",
        "ifrs-full:CashFlowsFromUsedInOperations",
    ),
    "capex": (
        "ifrs-full:PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities",
        "ifrs-full:PaymentsToAcquirePropertyPlantAndEquipment",
        "ifrs-full:PurchaseOfPropertyPlantAndEquipment",
    ),
    "borrowings_current": (
        "ifrs-full:CurrentBorrowings",
        "ifrs-full:CurrentPortionOfNoncurrentBorrowings",
    ),
    "borrowings_noncurrent": (
        "ifrs-full:NoncurrentBorrowings",
        "ifrs-full:LongtermBorrowings",
    ),
    "interest_expense": (
        "ifrs-full:InterestExpense",
        "ifrs-full:FinanceCosts",
    ),
    "shares": (
        "ifrs-full:WeightedAverageNumberOfSharesOutstanding",
        "ifrs-full:WeightedAverageNumberOfDilutedSharesOutstanding",
    ),
    "eps": (
        "ifrs-full:BasicEarningsLossPerShare",
        "ifrs-full:DilutedEarningsLossPerShare",
    ),
    "dividends": (
        "ifrs-full:DividendsPaid",
        "ifrs-full:DividendsPaidClassifiedAsFinancingActivities",
    ),
}


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "application/vnd.api+json, application/json",
        "Accept-Encoding": "gzip, deflate",
    })
    return s


def _country_for(ticker: str) -> str | None:
    u = str(ticker or "").upper()
    return next((country for suffix, country in _SUFFIX_COUNTRY.items() if u.endswith(suffix)), None)


def _resolve_isin(ticker: str) -> str | None:
    try:
        value = str(yf.Ticker(ticker).isin or "").strip().upper()
    except Exception:
        return None
    return value if _ISIN_RE.match(value) else None


def _resolve_lei(sess: requests.Session, isin: str) -> str | None:
    try:
        r = sess.get(GLEIF, params={"filter[isin]": isin, "page[size]": 5}, timeout=18)
        r.raise_for_status()
        rows = r.json().get("data") or []
        leis = {str(x.get("id") or "").strip() for x in rows if x.get("id")}
        if len(leis) != 1:
            return None
        lei = next(iter(leis))
        return lei if len(lei) == 20 else None
    except Exception as exc:
        log.debug("GLEIF %s: %s", isin, exc)
        return None


def _latest_filing(sess: requests.Session, lei: str, expected_country: str | None) -> dict | None:
    try:
        url = f"{ESEF}/api/entities/{lei}/filings"
        r = sess.get(url, params={"page[size]": 16}, timeout=20)
        r.raise_for_status()
        rows = r.json().get("data") or []
    except Exception as exc:
        log.debug("ESEF filings %s: %s", lei, exc)
        return None

    candidates = []
    for item in rows:
        a = item.get("attributes") or {}
        country = str(a.get("country") or "").upper()
        system = str(a.get("filing_system") or a.get("system") or "").upper()
        json_url = a.get("json_url") or a.get("xbrl_json_url")
        if not json_url:
            continue
        if expected_country and country and country != expected_country:
            continue
        if system and system not in ("ESEF", "UKSEF"):
            continue
        period = str(a.get("period_end") or a.get("report_date") or "")
        processed = str(a.get("processed") or a.get("date_added") or "")
        language = str(a.get("language") or "").lower()
        candidates.append((period, language == "en", processed, json_url, a))
    if not candidates:
        return None
    candidates.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
    period, _, _, json_url, attrs = candidates[0]
    return {"period_end": period, "json_url": urljoin(ESEF, json_url), "attributes": attrs}


def _parse_period(value: str) -> tuple[_dt.date | None, _dt.date | None]:
    if not value:
        return None, None
    try:
        if "/" in value:
            a, b = value.split("/", 1)
            return _dt.date.fromisoformat(a[:10]), _dt.date.fromisoformat(b[:10])
        instant = _dt.date.fromisoformat(value[:10])
        return None, instant - _dt.timedelta(days=1)
    except Exception:
        return None, None


def _numeric(value):
    try:
        v = float(value)
        return v if v == v and abs(v) != float("inf") else None
    except (TypeError, ValueError):
        return None


def _concept_rows(report: dict, concepts: tuple[str, ...], duration: bool | None = None) -> list[tuple[_dt.date, float]]:
    out = []
    for fact in (report.get("facts") or {}).values():
        dims = fact.get("dimensions") or {}
        if dims.get("concept") not in concepts:
            continue
        extras = set(dims) - {"concept", "entity", "period", "unit", "language"}
        if extras:
            continue
        value = _numeric(fact.get("value"))
        if value is None:
            continue
        start, end = _parse_period(str(dims.get("period") or ""))
        if end is None:
            continue
        is_duration = start is not None
        if duration is not None and is_duration != duration:
            continue
        if is_duration:
            days = (end - start).days
            if not 250 <= days <= 390:
                continue
        out.append((end, value))
    by_date: dict[_dt.date, set[float]] = {}
    for end, value in out:
        by_date.setdefault(end, set()).add(value)
    clean = [(d, next(iter(vals))) for d, vals in by_date.items() if len(vals) == 1]
    clean.sort(key=lambda x: x[0], reverse=True)
    return clean


def _latest_value(report: dict, key: str, duration: bool) -> float | None:
    rows = _concept_rows(report, _CONCEPTS[key], duration=duration)
    return rows[0][1] if rows else None


def _growth(report: dict, key: str) -> float | None:
    rows = _concept_rows(report, _CONCEPTS[key], duration=True)
    if len(rows) < 2 or rows[1][1] == 0:
        return None
    gap = abs((rows[0][0] - rows[1][0]).days)
    if not 300 <= gap <= 430:
        return None
    return rows[0][1] / rows[1][1] - 1


def _series_as_dict(report: dict, key: str, duration: bool, limit: int = 4) -> list[dict]:
    rows = _concept_rows(report, _CONCEPTS[key], duration=duration)
    return [{"date": d.isoformat(), "value": v} for d, v in rows[:limit]]


def _history(report: dict) -> list[dict]:
    rev = dict(_concept_rows(report, _CONCEPTS["revenue"], duration=True))
    ni = dict(_concept_rows(report, _CONCEPTS["net_income"], duration=True))
    op = dict(_concept_rows(report, _CONCEPTS["operating_income"], duration=True))
    gp = dict(_concept_rows(report, _CONCEPTS["gross_profit"], duration=True))
    assets = dict(_concept_rows(report, _CONCEPTS["assets"], duration=False))
    eq = dict(_concept_rows(report, _CONCEPTS["equity"], duration=False))
    cfo = dict(_concept_rows(report, _CONCEPTS["cfo"], duration=True))
    capex = dict(_concept_rows(report, _CONCEPTS["capex"], duration=True))
    dates = sorted(set(rev) | set(ni) | set(op) | set(gp), reverse=True)
    out = []
    for d in dates[:4]:
        r, n, o, g = rev.get(d), ni.get(d), op.get(d), gp.get(d)
        a, e = assets.get(d), eq.get(d)
        cf, cx = cfo.get(d), capex.get(d)
        row = {"date": d.isoformat()}
        if r not in (None, 0):
            if n is not None: row["net_margin"] = n / r
            if o is not None: row["operating_margin"] = o / r
            if g is not None: row["gross_margin"] = g / r
        if e not in (None, 0) and n is not None: row["roe"] = n / e
        if a not in (None, 0) and n is not None: row["roa"] = n / a
        if cf is not None and cx is not None and r not in (None, 0): row["fcf_margin"] = (cf - abs(cx)) / r
        if len(row) > 1:
            out.append(row)
    return out


def _fetch_report(sess: requests.Session, filing: dict) -> dict | None:
    try:
        r = sess.get(filing["json_url"], timeout=35)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        log.debug("ESEF report %s: %s", filing.get("json_url"), exc)
        return None


def enrich(raw, priority=None, max_nonpriority=180):
    priority = set(priority or [])
    sess = _session()
    non = 0
    enriched = 0

    for m in raw:
        ticker = str(getattr(m, "ticker", "") or "").upper()
        country = _country_for(ticker)
        if not country or getattr(m, "quote_type", None) in ("ETF", "CRYPTO"):
            continue
        missing = sum(getattr(m, k, None) is None for k in (
            "roe", "roa", "profit_margin", "operating_margin", "gross_margin",
            "revenue_growth", "free_cash_flow", "current_ratio", "quick_ratio",
            "debt_to_equity", "operating_cash_flow", "interest_expense",
        ))
        if missing < 2 and ticker not in priority:
            continue
        if ticker not in priority:
            non += 1
            if non > max_nonpriority:
                continue

        isin = _resolve_isin(ticker)
        if not isin:
            continue
        lei = _resolve_lei(sess, isin)
        if not lei:
            continue
        filing = _latest_filing(sess, lei, country)
        if not filing:
            continue
        report = _fetch_report(sess, filing)
        if not report:
            continue

        rev = _latest_value(report, "revenue", True)
        ni = _latest_value(report, "net_income", True)
        op = _latest_value(report, "operating_income", True)
        gp = _latest_value(report, "gross_profit", True)
        assets = _latest_value(report, "assets", False)
        equity = _latest_value(report, "equity", False)
        current_assets = _latest_value(report, "assets_current", False)
        current_liab = _latest_value(report, "liabilities_current", False)
        inventory = _latest_value(report, "inventory", False)
        cash = _latest_value(report, "cash", False)
        cfo = _latest_value(report, "cfo", True)
        capex = _latest_value(report, "capex", True)
        dcur = _latest_value(report, "borrowings_current", False)
        dnon = _latest_value(report, "borrowings_noncurrent", False)
        interest = _latest_value(report, "interest_expense", True)
        debt = (dcur or 0) + (dnon or 0) if dcur is not None or dnon is not None else None

        if getattr(m, "profit_margin", None) is None and rev not in (None, 0) and ni is not None: m.profit_margin = ni / rev
        if getattr(m, "operating_margin", None) is None and rev not in (None, 0) and op is not None: m.operating_margin = op / rev
        if getattr(m, "gross_margin", None) is None and rev not in (None, 0) and gp is not None: m.gross_margin = gp / rev
        if getattr(m, "roe", None) is None and equity not in (None, 0) and ni is not None: m.roe = ni / equity
        if getattr(m, "roa", None) is None and assets not in (None, 0) and ni is not None: m.roa = ni / assets
        if getattr(m, "total_assets", None) is None: m.total_assets = assets
        if getattr(m, "stockholders_equity", None) is None: m.stockholders_equity = equity
        if getattr(m, "current_ratio", None) is None and current_liab not in (None, 0) and current_assets is not None: m.current_ratio = current_assets / current_liab
        if getattr(m, "quick_ratio", None) is None and current_liab not in (None, 0) and current_assets is not None:
            m.quick_ratio = (current_assets - (inventory or 0)) / current_liab
        if getattr(m, "total_cash", None) is None: m.total_cash = cash
        if getattr(m, "total_debt", None) is None: m.total_debt = debt
        if getattr(m, "debt_to_equity", None) is None and equity not in (None, 0) and debt is not None: m.debt_to_equity = debt / equity
        if getattr(m, "operating_cash_flow", None) is None: m.operating_cash_flow = cfo
        if getattr(m, "free_cash_flow", None) is None and cfo is not None and capex is not None: m.free_cash_flow = cfo - abs(capex)
        if getattr(m, "ebit", None) is None and op is not None: m.ebit = op
        if getattr(m, "interest_expense", None) is None and interest is not None: m.interest_expense = abs(interest)
        if getattr(m, "revenue_growth", None) is None: m.revenue_growth = _growth(report, "revenue")
        if getattr(m, "earnings_growth", None) is None: m.earnings_growth = _growth(report, "net_income")

        if not getattr(m, "annual_quality_history", None):
            m.annual_quality_history = _history(report)
        if not getattr(m, "quarterly_revenue", None):
            # ESEF filings are primarily annual; keep the generic series only as
            # annual fallback and never label it quarterly.
            pass
        if not getattr(m, "annual_dividend_history", None):
            m.annual_dividend_history = _series_as_dict(report, "dividends", True, 4)

        # A statement-derived ROCE proxy is useful when Yahoo omits it. This is
        # deliberately conservative: equity + debt - cash approximates invested
        # capital and is not used when the denominator is non-positive.
        if getattr(m, "roce_proxy", None) is None and op is not None:
            invested = None
            if equity is not None or debt is not None or cash is not None:
                invested = (equity or 0) + (debt or 0) - (cash or 0)
            if invested is not None and invested > 0:
                m.roce_proxy = op / invested

        m.isin = isin
        m.lei = lei
        m.esef_period_end = filing.get("period_end")
        m.esef_enriched = True
        enriched += 1
        time.sleep(0.06)

    log.info("ESEF/UKSEF enriched %d rows", enriched)
    return raw
