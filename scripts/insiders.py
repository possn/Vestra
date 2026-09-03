"""
insiders.py — US insider transactions from SEC EDGAR (official, free, no API key).

The module resolves ticker -> CIK, checks recent Form 4 filings and parses the
structured ownership XML. Successfully parsed filing accessions are immutable SEC
records, so their parsed result is cached in data/insider_filings_cache.json and
reused on later rebuilds. Failed/HTML/unparseable filings are never cached and
remain eligible for a later retry.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree as ET

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

log = logging.getLogger("insiders")

_DIAG_LOG_LIMIT = 15
_diag_logged = 0

SEC_USER_AGENT = os.getenv("SEC_USER_AGENT") or "Finscanner research-tool finscanner-app@proton.me"
HEADERS = {
    "User-Agent": SEC_USER_AGENT,
    "Accept-Encoding": "gzip, deflate",
    "Accept": "application/json, application/xml, text/xml, text/html, */*",
}
TICKER_CIK_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
ARCHIVE_URL = "https://www.sec.gov/Archives/edgar/data/{cik_int}/{accession}/{document}"
CACHE_PATH = Path(__file__).resolve().parents[1] / "data" / "insider_filings_cache.json"
CACHE_SCHEMA_VERSION = 1
CACHE_RETENTION_DAYS = 400

_ticker_to_cik: dict[str, str] | None = None
_lock = threading.Lock()
_last_request_at = 0.0
MIN_REQUEST_INTERVAL = float(os.getenv("FINSCANNER_SEC_MIN_INTERVAL", "0.13"))
SEC_WORKERS = max(1, min(4, int(os.getenv("FINSCANNER_SEC_WORKERS", "3"))))

_cache_lock = threading.Lock()
_filing_cache: dict[str, dict] | None = None
_cache_dirty = False


def _session() -> requests.Session:
    s = requests.Session()
    retry = Retry(
        total=4,
        connect=4,
        read=4,
        status=4,
        backoff_factor=0.8,
        status_forcelist=(403, 408, 429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET"]),
        respect_retry_after_header=True,
    )
    s.mount("https://", HTTPAdapter(max_retries=retry, pool_connections=8, pool_maxsize=8))
    s.headers.update(HEADERS)
    return s


_TLS = threading.local()


def _get_session() -> requests.Session:
    if not hasattr(_TLS, "session"):
        _TLS.session = _session()
    return _TLS.session


def _throttle():
    global _last_request_at
    with _lock:
        now = time.monotonic()
        wait = MIN_REQUEST_INTERVAL - (now - _last_request_at)
        if wait > 0:
            time.sleep(wait)
        _last_request_at = time.monotonic()


def _get(url: str, timeout: int = 25):
    _throttle()
    r = _get_session().get(url, timeout=timeout)
    r.raise_for_status()
    return r


def _load_ticker_cik_map() -> dict[str, str]:
    global _ticker_to_cik
    if _ticker_to_cik is not None:
        return _ticker_to_cik
    try:
        data = _get(TICKER_CIK_URL).json()
        _ticker_to_cik = {
            row["ticker"].upper(): str(row["cik_str"]).zfill(10)
            for row in data.values()
            if row.get("ticker") and row.get("cik_str") is not None
        }
    except Exception as e:
        log.warning("Could not load SEC ticker->CIK map (%s)", e)
        _ticker_to_cik = {}
    return _ticker_to_cik


def _cache_key(cik: str, accession: str) -> str:
    try:
        cik_key = str(int(str(cik)))
    except Exception:
        cik_key = str(cik or "").strip()
    return f"{cik_key}:{str(accession or '').strip()}"


def _load_filing_cache(path: Path = CACHE_PATH) -> dict[str, dict]:
    global _filing_cache
    with _cache_lock:
        if _filing_cache is not None and path == CACHE_PATH:
            return _filing_cache
        rows: dict[str, dict] = {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("schema_version") != CACHE_SCHEMA_VERSION or not isinstance(payload.get("filings"), dict):
                raise ValueError("unsupported insider filing cache schema")
            for key, row in payload["filings"].items():
                if not isinstance(row, dict):
                    continue
                raw_count = row.get("raw_nonderivative_transactions")
                accession = str(row.get("accession") or "").strip()
                transactions = row.get("transactions")
                if accession and isinstance(raw_count, int) and raw_count > 0 and isinstance(transactions, list):
                    rows[str(key)] = row
        except FileNotFoundError:
            pass
        except Exception as exc:
            log.warning("Insider filing cache unavailable; rebuilding from SEC: %s", exc)
        if path == CACHE_PATH:
            _filing_cache = rows
        return rows


def _cached_filing(cik: str, filing: dict, ticker: str):
    cache = _load_filing_cache()
    key = _cache_key(cik, filing.get("accession"))
    with _cache_lock:
        row = cache.get(key)
        if not row:
            return None
        transactions = []
        for tx in row.get("transactions") or []:
            if isinstance(tx, dict):
                copied = dict(tx)
                copied["ticker"] = ticker
                transactions.append(copied)
        return transactions, int(row["raw_nonderivative_transactions"]), "cache"


def _store_cached_filing(cik: str, filing: dict, transactions: list[dict], raw_count: int):
    global _cache_dirty
    if not isinstance(raw_count, int) or raw_count <= 0:
        return
    accession = str(filing.get("accession") or "").strip()
    if not accession:
        return
    cache = _load_filing_cache()
    row = {
        "cik": str(cik),
        "accession": accession,
        "filing_date": filing.get("filing_date"),
        "raw_nonderivative_transactions": raw_count,
        "transactions": [dict(tx) for tx in transactions if isinstance(tx, dict)],
        "source": "SEC EDGAR Form 4",
    }
    key = _cache_key(cik, accession)
    with _cache_lock:
        if cache.get(key) != row:
            cache[key] = row
            _cache_dirty = True


def _save_filing_cache(path: Path = CACHE_PATH):
    global _cache_dirty, _filing_cache
    with _cache_lock:
        if not _cache_dirty and path == CACHE_PATH:
            return
        cache = dict(_filing_cache or {}) if path == CACHE_PATH else dict(_load_filing_cache(path))
        cutoff = dt.date.today() - dt.timedelta(days=CACHE_RETENTION_DAYS)
        kept = {}
        for key, row in cache.items():
            try:
                filing_date = dt.date.fromisoformat(str(row.get("filing_date") or ""))
            except Exception:
                continue
            if filing_date >= cutoff:
                kept[key] = row
        payload = {
            "schema_version": CACHE_SCHEMA_VERSION,
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "source": "SEC EDGAR Form 4 immutable accession cache",
            "filing_count": len(kept),
            "filings": dict(sorted(kept.items())),
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)
        if path == CACHE_PATH:
            _filing_cache = kept
            _cache_dirty = False
        log.info("Insider filing cache: %d immutable accession(s)", len(kept))


def _text(node, path: str):
    x = node.find(path)
    if x is None or x.text is None:
        return None
    return x.text.strip()


def _float(node, path: str):
    v = _text(node, path)
    if v in (None, ""):
        return None
    try:
        return float(v.replace(",", ""))
    except (TypeError, ValueError):
        return None


def _bool_text(root, path: str) -> bool:
    v = (_text(root, path) or "").strip().lower()
    return v in {"1", "true", "yes", "x"}


def _parse_ownership_xml(content: bytes, ticker: str, accession: str) -> tuple[list[dict], int]:
    try:
        root = ET.fromstring(content)
    except Exception:
        return [], 0
    for elem in root.iter():
        if "}" in elem.tag:
            elem.tag = elem.tag.split("}", 1)[1]
    raw = root.findall("./nonDerivativeTable/nonDerivativeTransaction")
    owner = _text(root, "./reportingOwner/reportingOwnerId/rptOwnerName")
    rel = root.find("./reportingOwner/reportingOwnerRelationship")
    roles = []
    if rel is not None:
        if _bool_text(rel, "./isDirector"): roles.append("Director")
        if _bool_text(rel, "./isOfficer"): roles.append(_text(rel, "./officerTitle") or "Officer")
        if _bool_text(rel, "./isTenPercentOwner"): roles.append("10% owner")
        if _bool_text(rel, "./isOther"): roles.append("Other")
    out = []
    for tx in raw:
        code = _text(tx, "./transactionCoding/transactionCode")
        if code not in {"P", "S"}:
            continue
        shares = _float(tx, "./transactionAmounts/transactionShares/value")
        price = _float(tx, "./transactionAmounts/transactionPricePerShare/value")
        acq_disp = _text(tx, "./transactionAmounts/transactionAcquiredDisposedCode/value")
        date = _text(tx, "./transactionDate/value")
        value = shares * price if shares is not None and price is not None else None
        out.append({
            "ticker": ticker,
            "accession": accession,
            "date": date,
            "owner": owner,
            "role": ", ".join(r for r in roles if r) or None,
            "type": "buy" if code == "P" else "sell",
            "code": code,
            "shares": shares,
            "price": price,
            "value": value,
            "acquired_disposed": acq_disp,
        })
    return out, len(raw)


def _recent_form4_rows(cik: str, days: int) -> list[dict]:
    data = _get(SUBMISSIONS_URL.format(cik=cik)).json()
    recent = (data.get("filings") or {}).get("recent") or {}
    cutoff = dt.date.today() - dt.timedelta(days=days)
    rows = []
    for form, date_s, acc, doc in zip(
        recent.get("form") or [], recent.get("filingDate") or [],
        recent.get("accessionNumber") or [], recent.get("primaryDocument") or []
    ):
        if form not in {"4", "4/A"}:
            continue
        try:
            filing_date = dt.date.fromisoformat(date_s)
        except Exception:
            continue
        if filing_date < cutoff:
            continue
        rows.append({"filing_date": date_s, "accession": acc, "primary_document": doc})
    return rows


def _document_candidates(primary: str) -> list[str]:
    primary = (primary or "").strip()
    if not primary:
        return []
    p = PurePosixPath(primary)
    out = []
    if len(p.parts) > 1 and p.parts[0].lower().startswith("xsl"):
        out.append(str(PurePosixPath(*p.parts[1:])))
    if p.suffix.lower() in {".htm", ".html"}:
        out.append(str(p.with_suffix(".xml")))
    out.append(primary)
    return list(dict.fromkeys(out))


def _fetch_structured_filing(cik: str, filing: dict, ticker: str) -> tuple[list[dict], int, str | None]:
    cached = _cached_filing(cik, filing, ticker)
    if cached is not None:
        return cached

    cik_int = str(int(cik))
    accession_no_dash = filing["accession"].replace("-", "")
    last_error = None
    for document in _document_candidates(filing.get("primary_document") or ""):
        url = ARCHIVE_URL.format(cik_int=cik_int, accession=accession_no_dash, document=document)
        try:
            resp = _get(url)
            parsed, raw_count = _parse_ownership_xml(resp.content, ticker, filing["accession"])
            if raw_count > 0 or parsed:
                _store_cached_filing(cik, filing, parsed, raw_count)
                return parsed, raw_count, document
            snippet = resp.content[:200].decode("utf-8", errors="replace").replace("\n", " ")
            last_error = f"fetched {url} (HTTP {resp.status_code}, {len(resp.content)} bytes) but found 0 transactions — content starts: {snippet!r}"
        except requests.HTTPError as e:
            status = e.response.status_code if e.response is not None else "?"
            last_error = f"HTTP {status} fetching {url}"
        except Exception as e:
            last_error = f"{type(e).__name__}: {e} (url={url})"
    return [], 0, last_error


def insider_activity(ticker: str, days: int = 365, max_detail_filings: int = 12) -> dict:
    if "." in ticker:
        return {"status": "not_available", "reason": "non_us"}
    cik = _load_ticker_cik_map().get(ticker.upper())
    if not cik:
        return {"status": "not_available", "reason": "no_cik"}
    try:
        filings = _recent_form4_rows(cik, days)
    except Exception as e:
        return {"status": "not_available", "reason": "submissions_error", "error": str(e)[:160]}

    transactions = []
    raw_tx_seen = fetch_errors = 0
    xml_documents = 0
    for filing in filings[:max_detail_filings]:
        parsed, raw_count, detail = _fetch_structured_filing(cik, filing, ticker)
        if raw_count > 0:
            raw_tx_seen += raw_count
            xml_documents += 1
            transactions.extend(parsed)
        else:
            fetch_errors += 1
            if detail:
                global _diag_logged
                if _diag_logged < _DIAG_LOG_LIMIT:
                    log.info("%s %s detail unavailable: %s", ticker, filing["accession"], detail)
                    _diag_logged += 1
                else:
                    log.debug("%s %s detail unavailable: %s", ticker, filing["accession"], detail)

    transactions.sort(key=lambda x: x.get("date") or "", reverse=True)
    today = dt.date.today()
    cutoff30 = today - dt.timedelta(days=30)

    def tx_date(x):
        try:
            return dt.date.fromisoformat(x.get("date") or "")
        except Exception:
            return None

    tx30 = [x for x in transactions if (tx_date(x) is not None and tx_date(x) >= cutoff30)]
    buys30 = [x for x in tx30 if x["type"] == "buy"]
    sells30 = [x for x in tx30 if x["type"] == "sell"]
    buys365 = [x for x in transactions if x["type"] == "buy"]
    sells365 = [x for x in transactions if x["type"] == "sell"]

    def sum_known(items):
        vals = [x["value"] for x in items if x.get("value") is not None]
        return sum(vals) if vals else 0.0

    buy30, sell30 = sum_known(buys30), sum_known(sells30)
    buy365, sell365 = sum_known(buys365), sum_known(sells365)
    form4_30d = 0
    for filing in filings:
        try:
            if dt.date.fromisoformat(filing.get("filing_date") or "") >= cutoff30:
                form4_30d += 1
        except Exception:
            pass

    status = "ok" if not filings or xml_documents > 0 else "degraded"
    return {
        "status": status,
        "reason": None if status == "ok" else "form4_xml_unavailable",
        "form4_count_30d": form4_30d,
        "buy_count_30d": len(buys30) if status == "ok" else None,
        "sell_count_30d": len(sells30) if status == "ok" else None,
        "buy_value_30d": buy30 if status == "ok" else None,
        "sell_value_30d": sell30 if status == "ok" else None,
        "net_value_30d": (buy30 - sell30) if status == "ok" else None,
        "transactions": tx30[:12],
        "form4_count_365d": len(filings),
        "buy_count_365d": len(buys365) if status == "ok" else None,
        "sell_count_365d": len(sells365) if status == "ok" else None,
        "buy_value_365d": buy365 if status == "ok" else None,
        "sell_value_365d": sell365 if status == "ok" else None,
        "net_value_365d": (buy365 - sell365) if status == "ok" else None,
        "transactions_365d": transactions[:40],
        "detail_filings_parsed": xml_documents,
        "raw_nonderivative_transactions": raw_tx_seen,
        "fetch_errors": fetch_errors,
    }


def annotate(tickers: list[str], pause: float = 0.0) -> dict[str, dict]:
    _load_filing_cache()
    cik_map = _load_ticker_cik_map()
    log.info("SEC ticker->CIK map loaded with %d entries", len(cik_map))
    unique = sorted(set(t.upper() for t in tickers if t and "." not in t))
    out: dict[str, dict] = {}
    if not unique:
        return out
    with ThreadPoolExecutor(max_workers=SEC_WORKERS) as pool:
        futs = {pool.submit(insider_activity, tk): tk for tk in unique}
        for i, fut in enumerate(as_completed(futs), 1):
            tk = futs[fut]
            try:
                out[tk] = fut.result()
            except Exception as e:
                out[tk] = {"status": "not_available", "reason": "worker_error", "error": str(e)[:160]}
            if i % 50 == 0 or i == len(unique):
                log.info("insider intelligence %d/%d", i, len(unique))
    _save_filing_cache()
    return out
