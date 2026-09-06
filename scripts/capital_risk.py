"""SEC filing scanner for capital-structure and corporate-action risk.

Reads recent SEC submissions/primary filing documents for US-listed equities and
adds auditable flags to RawMetrics. It is intentionally conservative: no fuzzy
issuer matching and no score is created here; score.py decides how flags cap the
investment score.

A validated previous result may be reused only when the current SEC submissions
produce the exact same relevant-filing fingerprint and the scanner rule version
also matches. We still fetch submissions every run, so a new/amended accession
invalidates the cache immediately; unchanged issuers avoid re-downloading the
same filing documents.
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

log = logging.getLogger("capital_risk")
SEC_DATA = "https://data.sec.gov"
SEC_ARCHIVES = "https://www.sec.gov/Archives/edgar/data"
TICKERS = "https://www.sec.gov/files/company_tickers.json"
FORMS = {"8-K", "6-K", "20-F", "10-K", "S-1", "S-3", "F-1", "F-3", "424B3", "424B5", "DEF 14A"}
CAPITAL_RISK_SCANNER_VERSION = "capital-risk-v1-2026-09-06"
PREVIOUS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "stocks.json")


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
        out.append({"accession": acc, "date": str(filed), "form": form, "doc": doc})
    return out


def _filings_fingerprint(rows: list[dict]) -> str:
    """Stable identity of every currently relevant filing in the 730-day window."""
    parts = []
    for row in rows or []:
        parts.append("\x1f".join((
            str(row.get("accession") or ""),
            str(row.get("date") or ""),
            str(row.get("form") or ""),
            str(row.get("doc") or ""),
        )))
    payload = "\x1e".join(sorted(parts)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _load_previous(path: str | None = None) -> dict[str, dict]:
    """Load only previously validated/published capital-risk evidence."""
    source = path or PREVIOUS_PATH
    try:
        with open(source, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except Exception:
        return {}
    out = {}
    for row in payload.get("stocks") or []:
        if not isinstance(row, dict) or not row.get("capital_risk_checked"):
            continue
        ticker = str(row.get("ticker") or "").strip().upper()
        if ticker:
            out[ticker] = row
    return out


def _apply_previous_if_unchanged(m, previous: dict | None, fingerprint: str) -> bool:
    """Reuse a previous result only when inputs and scanner rules are identical."""
    if not isinstance(previous, dict):
        return False
    if previous.get("capital_risk_scanner_version") != CAPITAL_RISK_SCANNER_VERSION:
        return False
    if previous.get("capital_risk_filings_fingerprint") != fingerprint:
        return False

    fields = (
        "capital_structure_flags",
        "capital_structure_risk",
        "reverse_split_count_24m",
        "reverse_split_latest_date",
        "capital_risk_filings_checked",
    )
    for key in fields:
        setattr(m, key, previous.get(key))
    setattr(m, "capital_risk_checked", True)
    setattr(m, "capital_risk_filings_fingerprint", fingerprint)
    setattr(m, "capital_risk_scanner_version", CAPITAL_RISK_SCANNER_VERSION)
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


def _scan_docs(sess, cik: int, rows: list[dict], max_docs: int = 8):
    flags = set()
    reverse_dates = set()
    latest_reverse = None
    inspected = 0

    # Prioritise filings most likely to disclose financing/listing events.
    order = {"8-K": 0, "6-K": 0, "424B5": 1, "424B3": 1, "S-3": 2, "F-3": 2, "S-1": 2, "F-1": 2, "10-K": 3, "20-F": 3, "DEF 14A": 4}
    rows = sorted(rows, key=lambda r: (order.get(r["form"], 9), r["date"]), reverse=False)

    for row in rows[:max_docs]:
        acc = row["accession"].replace("-", "")
        url = f"{SEC_ARCHIVES}/{cik}/{acc}/{row['doc']}"
        try:
            resp = sess.get(url, timeout=18)
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

    if len(reverse_dates) >= 1:
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


def enrich(raw, priority=None, max_nonpriority=120):
    ua = os.getenv("SEC_USER_AGENT", "Vestra/4.2 (+https://github.com/possn/Vestra)").strip()
    if not ua:
        return raw
    priority = {str(x).upper() for x in (priority or [])}
    previous = _load_previous()
    sess = requests.Session()
    sess.headers.update({"User-Agent": ua, "Accept-Encoding": "gzip, deflate"})
    try:
        j = sess.get(TICKERS, timeout=20).json()
        cmap = {str(v.get("ticker", "")).upper(): int(v["cik_str"]) for v in j.values() if v.get("ticker") and v.get("cik_str")}
    except Exception as exc:
        log.warning("SEC ticker map unavailable for capital risk: %s", exc)
        return raw

    non = 0
    checked = 0
    flagged = 0
    reused = 0
    rescanned = 0
    for m in raw:
        t = str(getattr(m, "ticker", "") or "").upper()
        if t not in cmap or not _candidate(m, priority):
            continue
        if t not in priority:
            non += 1
            if non > max_nonpriority:
                continue
        try:
            sub = sess.get(f"{SEC_DATA}/submissions/CIK{cmap[t]:010d}.json", timeout=18).json()
            rows = _recent_rows(sub)
            fingerprint = _filings_fingerprint(rows)
            if _apply_previous_if_unchanged(m, previous.get(t), fingerprint):
                result = previous[t]
                reused += 1
            else:
                result = _scan_docs(sess, cmap[t], rows)
                for k, v in result.items():
                    setattr(m, k, v)
                setattr(m, "capital_risk_checked", True)
                setattr(m, "capital_risk_filings_fingerprint", fingerprint)
                setattr(m, "capital_risk_scanner_version", CAPITAL_RISK_SCANNER_VERSION)
                setattr(m, "capital_risk_reused", False)
                rescanned += 1
            checked += 1
            if result.get("capital_structure_flags"):
                flagged += 1
            time.sleep(0.11)
        except Exception as exc:
            log.debug("Capital risk %s: %s", t, exc)
    log.info(
        "Capital-structure risk checked %d issuers; %d flagged; %d unchanged reused; %d rescanned",
        checked, flagged, reused, rescanned,
    )
    return raw
