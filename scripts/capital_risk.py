"""SEC filing scanner for capital-structure and corporate-action risk.

Reads recent official SEC filings for US-listed equities and adds auditable flags
to RawMetrics. Exact ticker->CIK identity is used throughout; no fuzzy issuer
matching is permitted and score.py remains the only place that applies risk caps.

`data.sec.gov/submissions` is preferred when the GitHub runner can reach it. When
that API is blocked, the scanner discovers the same issuer filings through SEC
EDGAR quarterly `master.idx` files and scans the immutable full-submission text in
`www.sec.gov/Archives`. Thus a CompanyFacts/API outage must not silently disable
the capital-structure Risk Gate.

A previous result may be reused only when the current relevant-filing fingerprint
and the explicit scanner-rule version are identical. Discovery still runs every
build, so a new/amended accession invalidates the cache immediately. The cache is
stored under data/ and is published only by a coverage-guarded successful build.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import logging
import os
import re
import time
from html import unescape

import requests

from asset_types import is_equity_candidate
from sec_archives_enrich import (
    ARCHIVES_BASE,
    ArchiveClient,
    master_index_url,
    parse_master_index,
    recent_quarters,
)
from sec_enrich import TICKER_MAP_SNAPSHOT, _read_ticker_snapshot

log = logging.getLogger("capital_risk")
SEC_DATA = "https://data.sec.gov"
SEC_ARCHIVES = "https://www.sec.gov/Archives/edgar/data"
FORMS = {"8-K", "6-K", "20-F", "10-K", "S-1", "S-3", "F-1", "F-3", "424B3", "424B5", "DEF 14A"}
CAPITAL_RISK_SCANNER_VERSION = "capital-risk-v2-archives-fallback-2026-09-06"
CACHE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "capital_risk_cache.json")
CACHE_FIELDS = (
    "capital_structure_flags",
    "capital_structure_risk",
    "reverse_split_count_24m",
    "reverse_split_latest_date",
    "capital_risk_filings_checked",
)


def _text(html: str) -> str:
    html = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", " ", html or "")
    html = re.sub(r"(?s)<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", unescape(html)).strip().lower()


def _recent_rows(submissions: dict, days: int = 730):
    recent = (submissions.get("filings") or {}).get("recent") or {}
    cutoff = _dt.date.today() - _dt.timedelta(days=days)
    keys = ("accessionNumber", "filingDate", "form", "primaryDocument")
    cols = [recent.get(k) or [] for k in keys]
    out = []
    for acc, filed, form, doc in zip(*cols):
        try:
            d = _dt.date.fromisoformat(str(filed))
        except Exception:
            continue
        if d < cutoff or form not in FORMS or not acc or not doc:
            continue
        out.append({"accession": str(acc), "date": str(filed), "form": str(form), "doc": str(doc)})
    return out


def _archive_rows_by_cik(client=None, days: int = 730, quarter_count: int = 9):
    """Discover exact CIK filings from official EDGAR master indexes.

    Nine quarters safely cover the rolling 730-day window even near quarter
    boundaries. Master rows point at immutable full-submission .txt objects,
    which contain the primary filing plus exhibits and are sufficient for the
    conservative phrase scanner below.
    """
    client = client or ArchiveClient()
    cutoff = _dt.date.today() - _dt.timedelta(days=days)
    grouped: dict[int, list[dict]] = {}
    loaded = 0
    for year, quarter in recent_quarters(count=quarter_count):
        try:
            text = client.text(master_index_url(year, quarter), timeout=30)
        except Exception as exc:
            log.warning("Capital risk SEC Archives index %s Q%d unavailable: %s", year, quarter, exc)
            continue
        loaded += 1
        for row in parse_master_index(text, allowed_forms=FORMS):
            try:
                filed = _dt.date.fromisoformat(str(row.get("filed") or ""))
            except Exception:
                continue
            if filed < cutoff:
                continue
            filename = str(row.get("filename") or "")
            if not filename:
                continue
            normalized = {
                "accession": str(row.get("accession") or ""),
                "date": str(row.get("filed") or ""),
                "form": str(row.get("form") or ""),
                "doc": "",
                "archive_url": f"{ARCHIVES_BASE}{filename}",
            }
            grouped.setdefault(int(row["cik"]), []).append(normalized)
    log.info(
        "Capital-risk Archives discovery loaded %d/%d quarterly indexes; %d CIKs with relevant filings",
        loaded,
        quarter_count,
        len(grouped),
    )
    return grouped


def _filings_fingerprint(rows: list[dict]) -> str:
    """Stable identity of every currently relevant filing in the 730-day window."""
    parts = []
    for row in rows or []:
        parts.append("\x1f".join((
            str(row.get("accession") or ""),
            str(row.get("date") or ""),
            str(row.get("form") or ""),
            str(row.get("doc") or row.get("archive_url") or ""),
        )))
    payload = "\x1e".join(sorted(parts)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _load_previous(path: str | None = None) -> dict[str, dict]:
    source = path or CACHE_PATH
    try:
        with open(source, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except Exception:
        return {}
    if payload.get("scanner_version") != CAPITAL_RISK_SCANNER_VERSION:
        return {}
    rows = payload.get("rows") or {}
    return {
        str(ticker).strip().upper(): dict(row)
        for ticker, row in rows.items()
        if ticker and isinstance(row, dict)
    }


def _cache_record(result: dict, fingerprint: str) -> dict:
    return {
        "scanner_version": CAPITAL_RISK_SCANNER_VERSION,
        "filings_fingerprint": fingerprint,
        **{key: result.get(key) for key in CACHE_FIELDS},
    }


def _write_cache(rows: dict[str, dict], path: str | None = None) -> None:
    target = path or CACHE_PATH
    os.makedirs(os.path.dirname(target), exist_ok=True)
    tmp = f"{target}.tmp"
    payload = {
        "scanner_version": CAPITAL_RISK_SCANNER_VERSION,
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "rows": {ticker: rows[ticker] for ticker in sorted(rows)},
    }
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, target)


def _apply_previous_if_unchanged(m, previous: dict | None, fingerprint: str) -> bool:
    if not isinstance(previous, dict):
        return False
    if previous.get("scanner_version") != CAPITAL_RISK_SCANNER_VERSION:
        return False
    if previous.get("filings_fingerprint") != fingerprint:
        return False
    for key in CACHE_FIELDS:
        setattr(m, key, previous.get(key))
    setattr(m, "capital_risk_checked", True)
    setattr(m, "capital_risk_reused", True)
    return True


def _candidate(m, priority: set[str]) -> bool:
    t = str(getattr(m, "ticker", "") or "").upper()
    if not t or "." in t or not is_equity_candidate(getattr(m, "quote_type", None)):
        return False
    if t in priority:
        return True
    price = getattr(m, "current_price", None)
    cap = getattr(m, "market_cap", None)
    dilution = getattr(m, "diluted_shares_yoy", None)
    fcf = getattr(m, "free_cash_flow", None)
    if price is not None and price < 5:
        return True
    if cap is not None and cap < 500_000_000:
        return True
    if dilution is not None and dilution > 0.10:
        return True
    if cap and cap > 0 and fcf is not None and abs(fcf / cap) > 0.20:
        return True
    return False


def _scan_docs(client, cik: int, rows: list[dict], max_docs: int = 8):
    flags = set()
    reverse_dates = set()
    latest_reverse = None
    inspected = 0

    order = {"8-K": 0, "6-K": 0, "424B5": 1, "424B3": 1, "S-3": 2, "F-3": 2, "S-1": 2, "F-1": 2, "10-K": 3, "20-F": 3, "DEF 14A": 4}
    rows = sorted(rows, key=lambda r: (order.get(r["form"], 9), r["date"]), reverse=False)

    for row in rows[:max_docs]:
        acc = str(row["accession"]).replace("-", "")
        url = row.get("archive_url") or f"{SEC_ARCHIVES}/{cik}/{acc}/{row['doc']}"
        try:
            resp = client.get(url, timeout=18)
            if not resp.ok:
                continue
            txt = _text(resp.text)
            inspected += 1
        except Exception:
            continue

        reverse = "reverse stock split" in txt or "reverse share split" in txt
        effected = any(p in txt for p in ("effected a reverse", "reverse stock split became effective", "reverse share split became effective", "trading on a split-adjusted basis"))
        if reverse and effected:
            reverse_dates.add(row["date"])
            latest_reverse = max(latest_reverse or row["date"], row["date"])

        if "at-the-market offering" in txt or "atm sales agreement" in txt or "at the market offering" in txt:
            flags.add("atm_offering")
        if ("convertible note" in txt or "convertible senior note" in txt or "convertible debenture" in txt) and "conversion" in txt:
            flags.add("convertible_financing")
        variable_terms = (
            "discount to the market price", "discount to market price", "lowest closing price",
            "lowest trading price", "variable conversion price", "percentage of the lowest",
            "70% of the", "75% of the", "80% of the", "85% of the",
        )
        if ("convertible note" in txt or "convertible debenture" in txt) and any(p in txt for p in variable_terms):
            flags.add("variable_price_convertible")
        if "warrant" in txt and any(p in txt for p in ("offering", "exercise price", "issuable", "purchase warrant")):
            flags.add("warrants_outstanding")
        if any(p in txt for p in ("minimum bid price requirement", "minimum bid price", "regain compliance with nasdaq", "may be delisted", "delisting from nasdaq")):
            flags.add("listing_compliance_risk")
        if row["form"] in {"424B5", "424B3", "S-1", "S-3", "F-1", "F-3"} and any(p in txt for p in ("common stock offered", "ordinary shares offered", "equity line", "purchase agreement")):
            flags.add("equity_financing")
        time.sleep(0.11)

    if reverse_dates:
        flags.add("reverse_split_recent")
    if len(reverse_dates) >= 2:
        flags.add("repeated_reverse_splits")

    severity = "clear"
    severe_combo = "variable_price_convertible" in flags or (
        "repeated_reverse_splits" in flags and "listing_compliance_risk" in flags
    )
    if severe_combo:
        severity = "severe"
    elif len(flags & {"repeated_reverse_splits", "convertible_financing", "atm_offering", "equity_financing", "listing_compliance_risk"}) >= 2:
        severity = "high"
    elif flags:
        severity = "watch"

    return {
        "capital_structure_flags": sorted(flags),
        "capital_structure_risk": severity,
        "reverse_split_count_24m": len(reverse_dates),
        "reverse_split_latest_date": latest_reverse,
        "capital_risk_filings_checked": inspected,
    }


def _validated_ticker_map():
    cached = _read_ticker_snapshot(TICKER_MAP_SNAPSHOT)
    return cached[0] if cached else {}


def enrich(raw, priority=None, max_nonpriority=120):
    priority = {str(x).upper() for x in (priority or [])}
    previous = _load_previous()
    next_cache = dict(previous)
    cmap = _validated_ticker_map()
    if not cmap:
        log.warning("Capital risk unavailable: validated SEC ticker/CIK snapshot missing")
        return raw

    api_ua = os.getenv("SEC_USER_AGENT", "").strip()
    api_session = None
    if api_ua:
        api_session = requests.Session()
        api_session.headers.update({"User-Agent": api_ua, "Accept-Encoding": "gzip, deflate"})

    archive_client = ArchiveClient()
    archive_by_cik = None

    def archive_rows(cik):
        nonlocal archive_by_cik
        if archive_by_cik is None:
            archive_by_cik = _archive_rows_by_cik(archive_client)
        return list(archive_by_cik.get(int(cik), []))

    non = checked = flagged = reused = rescanned = 0
    api_discovery = archive_discovery = discovery_failed = 0

    for m in raw:
        t = str(getattr(m, "ticker", "") or "").upper()
        if t not in cmap or not _candidate(m, priority):
            continue
        if t not in priority:
            non += 1
            if non > max_nonpriority:
                continue

        cik = int(cmap[t])
        rows = []
        scan_client = archive_client

        if api_session is not None:
            try:
                resp = api_session.get(f"{SEC_DATA}/submissions/CIK{cik:010d}.json", timeout=18)
                resp.raise_for_status()
                rows = _recent_rows(resp.json())
                scan_client = api_session
                api_discovery += 1
            except Exception:
                rows = []

        if not rows:
            rows = archive_rows(cik)
            if rows:
                archive_discovery += 1
                scan_client = archive_client
            else:
                discovery_failed += 1

        try:
            fingerprint = _filings_fingerprint(rows)
            if _apply_previous_if_unchanged(m, previous.get(t), fingerprint):
                result = {key: previous[t].get(key) for key in CACHE_FIELDS}
                reused += 1
            else:
                result = _scan_docs(scan_client, cik, rows)
                for key, value in result.items():
                    setattr(m, key, value)
                setattr(m, "capital_risk_checked", True)
                setattr(m, "capital_risk_reused", False)
                rescanned += 1
            next_cache[t] = _cache_record(result, fingerprint)
            checked += 1
            if result.get("capital_structure_flags"):
                flagged += 1
            time.sleep(0.11)
        except Exception as exc:
            log.debug("Capital risk %s: %s", t, exc)

    try:
        _write_cache(next_cache)
    except Exception as exc:
        log.warning("Capital-risk cache write failed: %s", exc)

    log.info(
        "Capital-structure risk checked %d issuers; %d flagged; %d unchanged reused; %d rescanned; discovery api=%d archives=%d missing=%d",
        checked, flagged, reused, rescanned, api_discovery, archive_discovery, discovery_failed,
    )
    return raw
