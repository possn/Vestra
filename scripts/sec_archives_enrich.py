"""Official SEC EDGAR Archives XBRL fallback for US equities.

`data.sec.gov` CompanyFacts is the preferred SEC source when reachable. GitHub
hosted runners are currently denied on that API, while the same runners can read
immutable EDGAR Archives objects with Vestra's long-standing research-tool request
profile. This module provides a bounded, exact-identity fallback using only SEC
EDGAR:

1. load the already validated ticker->CIK snapshot;
2. read the current and previous EDGAR quarterly master indexes once;
3. select the latest 10-Q/10-K/20-F/40-F for each exact CIK;
4. discover the filing's extracted XBRL instance from its SEC filing index;
5. extract statement facts and fill only fields that are still missing.

No fuzzy issuer matching, zero filling, mirrors, proxy sources or Score changes are
used. Parsed immutable accessions are cached compactly so subsequent daily runs
usually need only the quarterly master indexes.
"""
from __future__ import annotations

import datetime as dt
import html as html_lib
import json
import logging
import math
import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from asset_types import is_equity_candidate
from sec_enrich import TICKER_MAP_SNAPSHOT, _read_ticker_snapshot

log = logging.getLogger("sec_archives_enrich")
ROOT = Path(__file__).resolve().parents[1]
CACHE_PATH = ROOT / "data" / "sec_archives_facts.json"
CACHE_SCHEMA_VERSION = 1
USER_AGENT = "Finscanner research-tool finscanner-app@proton.me"
ARCHIVES_BASE = "https://www.sec.gov/Archives/"
ALLOWED_FORMS = {"10-Q", "10-K", "20-F", "40-F"}
DEFAULT_QUARTERS = 4
DEFAULT_MAX_NONPRIORITY = 300
MIN_REQUEST_INTERVAL = 0.16

_TAGS = {
    "revenue": ("RevenueFromContractWithCustomerExcludingAssessedTax", "RevenueFromContractWithCustomerIncludingAssessedTax", "Revenues", "SalesRevenueNet"),
    "net_income": ("NetIncomeLoss", "ProfitLoss"),
    "gross_profit": ("GrossProfit",),
    "operating_income": ("OperatingIncomeLoss",),
    "assets": ("Assets",),
    "assets_current": ("AssetsCurrent",),
    "inventory": ("InventoryNet", "InventoryFinishedGoodsNetOfAllowancesCustomerAdvancesAndProgressBillings"),
    "liabilities_current": ("LiabilitiesCurrent",),
    "equity": ("StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"),
    "cash": ("CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"),
    "debt_current": ("LongTermDebtAndFinanceLeaseObligationsCurrent", "LongTermDebtCurrent"),
    "debt_noncurrent": ("LongTermDebtAndFinanceLeaseObligationsNoncurrent", "LongTermDebtNoncurrent"),
    "debt_short": ("ShortTermBorrowings",),
    "cfo": ("NetCashProvidedByUsedInOperatingActivities", "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"),
    "capex": ("PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsForAdditionsToPropertyPlantAndEquipment"),
    "interest_expense": ("InterestExpenseNonOperating", "InterestAndDebtExpense", "InterestExpense"),
    "dividends": ("PaymentsOfDividends", "PaymentsOfDividendsCommonStock"),
}
_WANTED_TAGS = {tag for tags in _TAGS.values() for tag in tags}
_EXCLUDED_XML_SUFFIXES = ("_cal.xml", "_def.xml", "_lab.xml", "_pre.xml", "filingsummary.xml")
_HREF_XML_RE = re.compile(r"href\s*=\s*[\"']([^\"']+?\.xml(?:\?[^\"']*)?)[\"']", re.I)
_TR_RE = re.compile(r"<tr\b[^>]*>.*?</tr>", re.I | re.S)


def _finite(value):
    try:
        out = float(value)
        return out if math.isfinite(out) else None
    except (TypeError, ValueError):
        return None


def recent_quarters(today=None, count=DEFAULT_QUARTERS):
    today = today or dt.date.today()
    year = int(today.year)
    quarter = (int(today.month) - 1) // 3 + 1
    out = []
    for _ in range(max(1, int(count))):
        out.append((year, quarter))
        quarter -= 1
        if quarter == 0:
            year -= 1
            quarter = 4
    return out


def master_index_url(year, quarter):
    return f"{ARCHIVES_BASE}edgar/full-index/{int(year)}/QTR{int(quarter)}/master.idx"


def parse_master_index(text, allowed_forms=ALLOWED_FORMS):
    """Parse exact CIK/form/date/filename rows from SEC master.idx."""
    rows = []
    for raw_line in str(text or "").splitlines():
        line = raw_line.strip()
        if not line or "|" not in line:
            continue
        parts = line.split("|", 4)
        if len(parts) != 5:
            continue
        cik_text, company, form, filed, filename = [part.strip() for part in parts]
        form = form.upper()
        if form not in set(allowed_forms or ()):
            continue
        try:
            cik = int(cik_text)
        except (TypeError, ValueError):
            continue
        if cik <= 0 or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", filed):
            continue
        if not filename.startswith("edgar/data/") or not filename.lower().endswith(".txt"):
            continue
        accession = Path(filename).stem
        if not re.fullmatch(r"\d{10}-\d{2}-\d{6}", accession):
            continue
        rows.append({
            "cik": cik,
            "company": company,
            "form": form,
            "filed": filed,
            "filename": filename,
            "accession": accession,
        })
    return rows


def latest_filings_by_cik(index_texts):
    latest = {}
    for text in index_texts or []:
        for row in parse_master_index(text):
            old = latest.get(row["cik"])
            if old is None or (row["filed"], row["accession"]) > (old["filed"], old["accession"]):
                latest[row["cik"]] = row
    return latest


def filing_index_url(filing):
    cik = int(filing["cik"])
    accession = str(filing["accession"])
    compact = accession.replace("-", "")
    return f"{ARCHIVES_BASE}edgar/data/{cik}/{compact}/{accession}-index.htm"


def find_xbrl_instance_url(index_html, index_url):
    """Find the extracted instance document, never a calculation/label schema."""
    html_text = str(index_html or "")
    preferred_rows = []
    for row in _TR_RE.findall(html_text):
        upper = re.sub(r"<[^>]+>", " ", row).upper()
        if "EXTRACTED XBRL INSTANCE DOCUMENT" in upper or "EX-101.INS" in upper:
            preferred_rows.append(row)
    search_spaces = preferred_rows + [html_text]
    seen = set()
    for space in search_spaces:
        for href in _HREF_XML_RE.findall(space):
            href = html_lib.unescape(href.strip())
            clean = href.split("?", 1)[0].lower()
            if any(clean.endswith(suffix) for suffix in _EXCLUDED_XML_SUFFIXES):
                continue
            absolute = urljoin(index_url, href)
            if absolute in seen:
                continue
            seen.add(absolute)
            return absolute
    return None


def _local_name(tag):
    text = str(tag or "")
    if "}" in text:
        return text.rsplit("}", 1)[-1]
    if ":" in text:
        return text.rsplit(":", 1)[-1]
    return text


def _parse_date(value):
    try:
        return dt.date.fromisoformat(str(value)[:10])
    except Exception:
        return None


def parse_xbrl_instance(xml_content):
    """Return normalized contexts and wanted numeric facts from an XBRL instance."""
    root = ET.fromstring(xml_content)
    contexts = {}
    period_end = None
    for elem in root.iter():
        if _local_name(elem.tag) == "DocumentPeriodEndDate" and elem.text:
            candidate = str(elem.text).strip()[:10]
            if _parse_date(candidate):
                period_end = candidate
                break

    for elem in root.iter():
        if _local_name(elem.tag) != "context":
            continue
        cid = elem.attrib.get("id")
        if not cid:
            continue
        start = end = instant = None
        for child in elem.iter():
            name = _local_name(child.tag)
            text = str(child.text or "").strip()[:10]
            if name == "startDate":
                start = text
            elif name == "endDate":
                end = text
            elif name == "instant":
                instant = text
        effective_end = instant or end
        duration_days = None
        a, b = _parse_date(start), _parse_date(end)
        if a and b:
            duration_days = (b - a).days + 1
        contexts[cid] = {
            "start": start,
            "end": effective_end,
            "instant": bool(instant),
            "duration_days": duration_days,
        }

    facts = {tag: [] for tag in _WANTED_TAGS}
    for elem in root.iter():
        name = _local_name(elem.tag)
        if name not in facts:
            continue
        context_ref = elem.attrib.get("contextRef")
        context = contexts.get(context_ref)
        if not context:
            continue
        nil_value = next((value for key, value in elem.attrib.items() if _local_name(key) == "nil"), None)
        if str(nil_value or "").lower() in ("true", "1"):
            continue
        text = str(elem.text or "").strip().replace(",", "")
        value = _finite(text)
        if value is None:
            continue
        facts[name].append({
            "val": value,
            "start": context.get("start"),
            "end": context.get("end"),
            "instant": bool(context.get("instant")),
            "duration_days": context.get("duration_days"),
            "unit": elem.attrib.get("unitRef"),
        })
    if not period_end:
        ends = [ctx.get("end") for ctx in contexts.values() if _parse_date(ctx.get("end"))]
        period_end = max(ends) if ends else None
    return {"period_end": period_end, "facts": facts}


def _rows_for_tags(parsed, tags):
    facts = (parsed or {}).get("facts") or {}
    for tag in tags:
        rows = list(facts.get(tag) or [])
        if rows:
            return rows
    return []


def _choose_instant(parsed, tags, period_end=None):
    rows = [row for row in _rows_for_tags(parsed, tags) if row.get("instant")]
    if not rows:
        return None
    target = str(period_end or parsed.get("period_end") or "")[:10]
    exact = [row for row in rows if str(row.get("end") or "")[:10] == target]
    pool = exact or rows
    pool.sort(key=lambda row: str(row.get("end") or ""), reverse=True)
    return pool[0]


def _choose_duration(parsed, tags, form, period_end=None, mode="income"):
    rows = [row for row in _rows_for_tags(parsed, tags) if not row.get("instant") and row.get("duration_days")]
    if not rows:
        return None
    target = str(period_end or parsed.get("period_end") or "")[:10]
    exact = [row for row in rows if str(row.get("end") or "")[:10] == target]
    pool = exact or rows
    form = str(form or "").upper()
    if mode == "cash":
        pool.sort(key=lambda row: (str(row.get("end") or ""), int(row.get("duration_days") or 0)), reverse=True)
        return pool[0]
    if form == "10-Q":
        quarterly = [row for row in pool if 60 <= int(row.get("duration_days") or 0) <= 120]
        if quarterly:
            quarterly.sort(key=lambda row: (abs(int(row.get("duration_days") or 0) - 91), str(row.get("end") or "")))
            return quarterly[0]
    annual = [row for row in pool if 250 <= int(row.get("duration_days") or 0) <= 430]
    if annual:
        annual.sort(key=lambda row: (abs(int(row.get("duration_days") or 0) - 365), str(row.get("end") or "")))
        return annual[0]
    pool.sort(key=lambda row: (str(row.get("end") or ""), -abs(int(row.get("duration_days") or 0) - 91)), reverse=True)
    return pool[0]


def _matching_duration(parsed, tags, reference):
    if not reference:
        return None
    rows = [row for row in _rows_for_tags(parsed, tags) if not row.get("instant")]
    exact = [row for row in rows if row.get("start") == reference.get("start") and row.get("end") == reference.get("end")]
    return exact[0] if exact else None


def _value(row):
    return _finite((row or {}).get("val"))


def _same_duration_growth(parsed, tags, current):
    if not current:
        return None
    current_value = _value(current)
    current_end = _parse_date(current.get("end"))
    current_days = int(current.get("duration_days") or 0)
    if current_value is None or not current_end or not current_days:
        return None
    candidates = []
    for row in _rows_for_tags(parsed, tags):
        if row is current or row.get("instant"):
            continue
        previous_value = _value(row)
        previous_end = _parse_date(row.get("end"))
        previous_days = int(row.get("duration_days") or 0)
        if previous_value in (None, 0) or not previous_end:
            continue
        day_delta = (current_end - previous_end).days
        if 330 <= day_delta <= 400 and abs(previous_days - current_days) <= 10:
            candidates.append((abs(day_delta - 365), row))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0])
    previous_value = _value(candidates[0][1])
    return current_value / previous_value - 1 if previous_value not in (None, 0) else None


def extract_metrics(parsed, form):
    period_end = (parsed or {}).get("period_end")
    revenue_row = _choose_duration(parsed, _TAGS["revenue"], form, period_end, "income")
    income_reference = revenue_row or _choose_duration(parsed, _TAGS["net_income"], form, period_end, "income")

    def income_value(key):
        row = _matching_duration(parsed, _TAGS[key], income_reference)
        if row is None:
            row = _choose_duration(parsed, _TAGS[key], form, period_end, "income")
        return _value(row)

    def instant_value(key):
        return _value(_choose_instant(parsed, _TAGS[key], period_end))

    revenue = _value(revenue_row) if revenue_row else income_value("revenue")
    net_income = income_value("net_income")
    gross_profit = income_value("gross_profit")
    operating_income = income_value("operating_income")
    assets = instant_value("assets")
    assets_current = instant_value("assets_current")
    inventory = instant_value("inventory")
    liabilities_current = instant_value("liabilities_current")
    equity = instant_value("equity")
    cash = instant_value("cash")

    debt_parts = [instant_value("debt_current"), instant_value("debt_noncurrent"), instant_value("debt_short")]
    debt = sum(value for value in debt_parts if value is not None) if any(value is not None for value in debt_parts) else None

    cfo_row = _choose_duration(parsed, _TAGS["cfo"], form, period_end, "cash")
    capex_row = _choose_duration(parsed, _TAGS["capex"], form, period_end, "cash")
    if cfo_row and capex_row and (cfo_row.get("start"), cfo_row.get("end")) != (capex_row.get("start"), capex_row.get("end")):
        matching_capex = _matching_duration(parsed, _TAGS["capex"], cfo_row)
        if matching_capex:
            capex_row = matching_capex
    cfo = _value(cfo_row)
    capex = _value(capex_row)
    interest = income_value("interest_expense")

    metrics = {
        "period_end": period_end,
        "revenue": revenue,
        "net_income": net_income,
        "gross_profit": gross_profit,
        "operating_income": operating_income,
        "assets": assets,
        "assets_current": assets_current,
        "inventory": inventory,
        "liabilities_current": liabilities_current,
        "equity": equity,
        "cash": cash,
        "debt": debt,
        "cfo": cfo,
        "capex": capex,
        "interest_expense": abs(interest) if interest is not None else None,
        "revenue_growth": _same_duration_growth(parsed, _TAGS["revenue"], revenue_row),
        "earnings_growth": _same_duration_growth(parsed, _TAGS["net_income"], _matching_duration(parsed, _TAGS["net_income"], income_reference) or _choose_duration(parsed, _TAGS["net_income"], form, period_end, "income")),
    }
    metrics["current_ratio"] = assets_current / liabilities_current if assets_current is not None and liabilities_current not in (None, 0) else None
    metrics["quick_ratio"] = (assets_current - (inventory or 0)) / liabilities_current if assets_current is not None and liabilities_current not in (None, 0) else None
    metrics["profit_margin"] = net_income / revenue if net_income is not None and revenue not in (None, 0) else None
    metrics["operating_margin"] = operating_income / revenue if operating_income is not None and revenue not in (None, 0) else None
    metrics["gross_margin"] = gross_profit / revenue if gross_profit is not None and revenue not in (None, 0) else None
    metrics["roe"] = net_income / equity if net_income is not None and equity not in (None, 0) else None
    metrics["roa"] = net_income / assets if net_income is not None and assets not in (None, 0) else None
    metrics["debt_to_equity"] = debt / equity if debt is not None and equity not in (None, 0) else None
    metrics["free_cash_flow"] = cfo - abs(capex) if cfo is not None and capex is not None else None
    metrics["roce_proxy"] = None
    invested = (equity or 0) + (debt or 0) - (cash or 0) if any(value is not None for value in (equity, debt, cash)) else None
    if operating_income is not None and invested is not None and invested > 0:
        metrics["roce_proxy"] = operating_income / invested
    return metrics


def _agreement(old, new, tolerance):
    old_value, new_value = _finite(old), _finite(new)
    if old_value is None or new_value is None:
        return None
    scale = max(abs(old_value), abs(new_value), 1.0)
    return abs(old_value - new_value) / scale <= tolerance


def apply_metrics(metrics_obj, values):
    """Apply observed SEC values non-destructively; return whether evidence was usable."""
    values = values or {}
    observed = [value for key, value in values.items() if key != "period_end" and _finite(value) is not None]
    if not observed:
        return False

    preexisting = {
        "total_cash": getattr(metrics_obj, "total_cash", None),
        "total_debt": getattr(metrics_obj, "total_debt", None),
        "current_ratio": getattr(metrics_obj, "current_ratio", None),
        "total_assets": getattr(metrics_obj, "total_assets", None),
        "stockholders_equity": getattr(metrics_obj, "stockholders_equity", None),
    }
    checks = []
    for field, sec_key, tolerance in (
        ("total_cash", "cash", .30),
        ("total_debt", "debt", .30),
        ("current_ratio", "current_ratio", .20),
        ("total_assets", "assets", .20),
        ("stockholders_equity", "equity", .20),
    ):
        agreed = _agreement(preexisting[field], values.get(sec_key), tolerance)
        if agreed is not None:
            checks.append(agreed)

    mapping = {
        "profit_margin": "profit_margin",
        "operating_margin": "operating_margin",
        "gross_margin": "gross_margin",
        "roe": "roe",
        "roa": "roa",
        "current_ratio": "current_ratio",
        "quick_ratio": "quick_ratio",
        "total_cash": "cash",
        "total_debt": "debt",
        "total_assets": "assets",
        "stockholders_equity": "equity",
        "debt_to_equity": "debt_to_equity",
        "operating_cash_flow": "cfo",
        "free_cash_flow": "free_cash_flow",
        "ebit": "operating_income",
        "interest_expense": "interest_expense",
        "revenue_growth": "revenue_growth",
        "earnings_growth": "earnings_growth",
        "roce_proxy": "roce_proxy",
    }
    for field, key in mapping.items():
        if getattr(metrics_obj, field, None) is None:
            value = _finite(values.get(key))
            if value is not None:
                setattr(metrics_obj, field, value)

    setattr(metrics_obj, "sec_period_end", values.get("period_end"))
    setattr(metrics_obj, "source_agreement_checks", len(checks))
    setattr(metrics_obj, "source_agreement_pct", round(sum(bool(item) for item in checks) / len(checks) * 100, 1) if checks else None)
    setattr(metrics_obj, "sec_edgar_enriched", True)
    setattr(metrics_obj, "sec_edgar_transport", "archives_xbrl")
    return True


def _load_cache(path=CACHE_PATH):
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if payload.get("schema_version") != CACHE_SCHEMA_VERSION or not isinstance(payload.get("entries"), dict):
            return {}
        return payload["entries"]
    except Exception:
        return {}


def _write_cache(entries, path=CACHE_PATH):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": CACHE_SCHEMA_VERSION,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "entries": entries,
    }
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    tmp.replace(path)


def _build_session():
    session = requests.Session()
    retry = Retry(
        total=2,
        connect=2,
        read=2,
        status=2,
        backoff_factor=.8,
        status_forcelist=(403, 408, 429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET"]),
        respect_retry_after_header=True,
    )
    session.mount("https://", HTTPAdapter(max_retries=retry, pool_connections=2, pool_maxsize=2))
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept-Encoding": "gzip, deflate",
        "Accept": "application/json, application/xml, text/xml, text/html, text/plain, */*",
    })
    return session


class ArchiveClient:
    def __init__(self, session=None, sleeper=time.sleep, interval=MIN_REQUEST_INTERVAL):
        self.session = session or _build_session()
        self.sleeper = sleeper
        self.interval = float(interval)
        self.last_request_at = 0.0
        self.requests = 0

    def get(self, url, timeout=25):
        now = time.monotonic()
        wait = self.interval - (now - self.last_request_at)
        if self.last_request_at and wait > 0:
            self.sleeper(wait)
        response = self.session.get(url, timeout=timeout)
        self.last_request_at = time.monotonic()
        self.requests += 1
        response.raise_for_status()
        return response

    def text(self, url, timeout=25):
        return self.get(url, timeout=timeout).text

    def content(self, url, timeout=25):
        return self.get(url, timeout=timeout).content


def _candidate_missing(metrics_obj):
    return sum(
        getattr(metrics_obj, key, None) is None
        for key in ("roe", "roa", "profit_margin", "operating_margin", "gross_margin", "revenue_growth", "free_cash_flow", "current_ratio", "quick_ratio", "debt_to_equity", "interest_expense")
    )


def enrich(raw, priority=None, max_nonpriority=DEFAULT_MAX_NONPRIORITY, client=None, cache_path=CACHE_PATH, quarters=None):
    cached_map = _read_ticker_snapshot(TICKER_MAP_SNAPSHOT)
    if not cached_map:
        log.warning("SEC Archives fallback unavailable: validated ticker/CIK snapshot missing")
        return raw
    cmap, _snapshot = cached_map
    client = client or ArchiveClient()

    index_texts = []
    for year, quarter in (quarters or recent_quarters()):
        try:
            index_texts.append(client.text(master_index_url(year, quarter), timeout=30))
        except Exception as exc:
            log.warning("SEC Archives master index %s Q%d unavailable: %s", year, quarter, exc)
    filings = latest_filings_by_cik(index_texts)
    if not filings:
        log.warning("SEC Archives fallback: no eligible filings found in quarterly indexes")
        return raw

    cache = _load_cache(cache_path)
    priority = {str(item).upper() for item in (priority or set())}
    nonpriority = 0
    attempted = enriched = cache_hits = network_parsed = filing_missing = parse_failed = 0
    cache_changed = False

    for metrics_obj in raw:
        ticker = str(getattr(metrics_obj, "ticker", "") or "").upper()
        if not ticker or "." in ticker or not is_equity_candidate(getattr(metrics_obj, "quote_type", None)):
            continue
        if getattr(metrics_obj, "sec_edgar_enriched", False):
            continue
        cik = cmap.get(ticker)
        if not cik:
            continue
        missing = _candidate_missing(metrics_obj)
        if missing < 2 and ticker not in priority:
            continue
        if ticker not in priority:
            nonpriority += 1
            if nonpriority > int(max_nonpriority):
                continue
        filing = filings.get(int(cik))
        if not filing:
            filing_missing += 1
            continue
        attempted += 1
        accession = filing["accession"]
        cached = cache.get(accession)
        values = None
        if isinstance(cached, dict) and int(cached.get("cik") or 0) == int(cik) and isinstance(cached.get("metrics"), dict):
            values = cached["metrics"]
            cache_hits += 1
        else:
            try:
                index_url = filing_index_url(filing)
                filing_html = client.text(index_url)
                instance_url = find_xbrl_instance_url(filing_html, index_url)
                if not instance_url:
                    raise ValueError("extracted XBRL instance not found")
                parsed = parse_xbrl_instance(client.content(instance_url, timeout=30))
                values = extract_metrics(parsed, filing["form"])
                if not any(_finite(value) is not None for key, value in values.items() if key != "period_end"):
                    raise ValueError("XBRL instance contained no supported numeric facts")
                cache[accession] = {
                    "cik": int(cik),
                    "form": filing["form"],
                    "filed": filing["filed"],
                    "instance_url": instance_url,
                    "metrics": values,
                }
                cache_changed = True
                network_parsed += 1
            except Exception as exc:
                parse_failed += 1
                log.debug("SEC Archives %s: %s", ticker, exc)
                continue
        if apply_metrics(metrics_obj, values):
            enriched += 1

    if cache_changed:
        try:
            _write_cache(cache, cache_path)
        except Exception as exc:
            log.warning("SEC Archives cache could not be persisted: %s", exc)
    log.info(
        "SEC Archives XBRL enriched %d rows (attempted=%d cache=%d network=%d filing_missing=%d parse_failed=%d requests=%d)",
        enriched, attempted, cache_hits, network_parsed, filing_missing, parse_failed, int(getattr(client, "requests", 0) or 0),
    )
    return raw
