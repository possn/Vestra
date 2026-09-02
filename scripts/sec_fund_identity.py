"""Official SEC fund identity diagnostics.

The preferred source is SEC ``company_tickers_mf.json``. Some hosted runners
are denied access to that bulk file even while other EDGAR endpoints remain
available. When that happens Vestra falls back to the SEC's own Fund Fast Search
(``/cgi-bin/series``), querying only unresolved US ticker candidates one by one.

The fallback is deliberately asymmetric: an exact SEC fund match can prove that
an unresolved ticker is a registered fund; no match never proves that the ticker
is an equity. Nothing here mutates ``stocks.json`` or any score.
"""
from __future__ import annotations

import datetime as dt
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import time
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
STOCKS_PATH = ROOT / "data" / "stocks.json"
SNAPSHOT_PATH = ROOT / "data" / "sec_fund_ticker_map.json"
AUDIT_PATH = ROOT / "data" / "sec_fund_identity_audit.json"
SEC_FUND_TICKERS = "https://www.sec.gov/files/company_tickers_mf.json"
SEC_FUND_SEARCH = "https://www.sec.gov/cgi-bin/series"
SCHEMA_VERSION = 2
SERIES_SENTINEL = "BUG"
US_REGIONS = {"UNITED STATES", "USA", "US"}
_CLASS_ID = re.compile(r"^C\d{9}$")
_SERIES_ID = re.compile(r"^S\d{9}$")
_CIK = re.compile(r"^\d{10}$")


def _normal_ticker(value):
    ticker = str(value or "").strip().upper()
    if not ticker or len(ticker) > 20:
        return None
    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-")
    return ticker if all(ch in allowed for ch in ticker) else None


def _normal_cik(value):
    try:
        cik = int(value)
    except (TypeError, ValueError):
        return None
    return cik if 0 < cik < 10_000_000_000 else None


def parse_sec_fund_payload(payload):
    """Parse the official SEC bulk fields/data schema fail-closed."""
    if not isinstance(payload, dict):
        return {}
    fields = payload.get("fields")
    rows = payload.get("data")
    if not isinstance(fields, list) or not isinstance(rows, list):
        return {}
    positions = {str(name).strip().lower(): i for i, name in enumerate(fields)}
    symbol_i = positions.get("symbol")
    cik_i = positions.get("cik")
    series_i = positions.get("seriesid")
    class_i = positions.get("classid")
    if symbol_i is None or cik_i is None:
        return {}

    out = {}
    for row in rows:
        if not isinstance(row, (list, tuple)):
            continue
        if symbol_i >= len(row) or cik_i >= len(row):
            continue
        ticker = _normal_ticker(row[symbol_i])
        cik = _normal_cik(row[cik_i])
        if not ticker or cik is None:
            continue
        item = {"cik": cik}
        if series_i is not None and series_i < len(row) and row[series_i]:
            item["series_id"] = str(row[series_i]).strip()
        if class_i is not None and class_i < len(row) and row[class_i]:
            item["class_id"] = str(row[class_i]).strip()
        out[ticker] = item
    return out


def _valid_map(mapping, min_count=1):
    if not isinstance(mapping, dict) or len(mapping) < min_count:
        return None
    out = {}
    for ticker, item in mapping.items():
        tk = _normal_ticker(ticker)
        if not tk or not isinstance(item, dict):
            return None
        cik = _normal_cik(item.get("cik"))
        if cik is None:
            return None
        clean = {"cik": cik}
        if item.get("series_id"):
            clean["series_id"] = str(item["series_id"])
        if item.get("class_id"):
            clean["class_id"] = str(item["class_id"])
        if item.get("class_name"):
            clean["class_name"] = str(item["class_name"]).strip()
        out[tk] = clean
    return out


class _SeriesTableParser(HTMLParser):
    """Collect visible table cells while ignoring search-form echo text."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self._row = None
        self._cell = None

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == "tr":
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = []

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in {"td", "th"} and self._row is not None and self._cell is not None:
            text = " ".join("".join(self._cell).split())
            self._row.append(text)
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self._row:
                self.rows.append(self._row)
            self._row = None
            self._cell = None


def parse_series_search_html(html, ticker):
    """Return exact SEC class identity for ticker, or None.

    SEC's result table is hierarchical: a CIK row is followed by a Series row,
    then one or more Class/Contract rows. We retain that context, but the final
    positive decision still requires Class ID + exact ticker in the same row.
    """
    ticker = _normal_ticker(ticker)
    if not ticker or not isinstance(html, str):
        return None
    parser = _SeriesTableParser()
    parser.feed(html)
    current_cik = None
    current_series = None
    for row in parser.rows:
        cells = [str(x or "").strip() for x in row]
        upper = [x.upper() for x in cells]

        cik_text = next((x for x in cells if _CIK.fullmatch(x)), None)
        if cik_text:
            current_cik = _normal_cik(cik_text)
            current_series = None

        series_id = next((x.upper() for x in cells if _SERIES_ID.fullmatch(x.upper())), None)
        if series_id:
            current_series = series_id

        class_id = next((x.upper() for x in cells if _CLASS_ID.fullmatch(x.upper())), None)
        if not class_id or ticker not in upper or current_cik is None:
            continue

        ticker_i = upper.index(ticker)
        name = cells[ticker_i - 1] if ticker_i > 0 else ""
        item = {"cik": current_cik, "class_id": class_id}
        if current_series:
            item["series_id"] = current_series
        if name and name.upper() not in {ticker, class_id}:
            item["class_name"] = name
        return item
    return None


def _mapping_from_response(response):
    response.raise_for_status()
    mapping = _valid_map(parse_sec_fund_payload(response.json()), min_count=1000)
    if not mapping:
        raise ValueError("SEC fund ticker payload did not pass validation")
    return mapping


def read_snapshot(path=None):
    path = Path(path or SNAPSHOT_PATH)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schema_version") not in {1, SCHEMA_VERSION}:
            return None
        mapping = _valid_map(payload.get("map"), min_count=1)
        if not mapping or int(payload.get("count") or 0) != len(mapping):
            return None
        return mapping, payload
    except Exception:
        return None


def write_snapshot(mapping, source=SEC_FUND_TICKERS, transport="direct_sec", scope="complete", path=None):
    mapping = _valid_map(mapping, min_count=1)
    if not mapping:
        raise ValueError("invalid SEC fund ticker map")
    path = Path(path or SNAPSHOT_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source": source,
        "transport": transport,
        "scope": scope,
        "count": len(mapping),
        "map": dict(sorted(mapping.items())),
    }
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
    return payload


def _session():
    import requests

    ua = os.getenv("SEC_USER_AGENT", "Vestra/4.0 (+https://github.com/possn/Vestra)").strip()
    sess = requests.Session()
    sess.headers.update({"User-Agent": ua, "Accept-Encoding": "gzip, deflate"})
    return sess


def fetch_remote(timeout=30, retries=3, session=None, sleep=time.sleep):
    """Fetch the complete SEC fund ticker map when the bulk file is available."""
    sess = session or _session()
    errors = []
    for attempt in range(1, max(1, int(retries)) + 1):
        try:
            response = sess.get(SEC_FUND_TICKERS, timeout=timeout, headers={"Accept": "application/json"})
            return _mapping_from_response(response)
        except Exception as exc:
            errors.append(f"attempt {attempt}: {exc}")
            if attempt < max(1, int(retries)):
                sleep(0.75 * attempt)
    raise RuntimeError("; ".join(errors[-3:]) or "SEC fund ticker map unavailable")


def fetch_series_exact(ticker, timeout=20, retries=2, session=None, sleep=time.sleep):
    """Resolve one ticker through the SEC Fund Fast Search, exact-match only."""
    ticker = _normal_ticker(ticker)
    if not ticker or "." in ticker:
        return None
    sess = session or _session()
    query = urlencode({"sc": "companyseries", "type": "N-PX", "ticker": ticker, "Find": "Search"})
    url = f"{SEC_FUND_SEARCH}?{query}"
    errors = []
    for attempt in range(1, max(1, int(retries)) + 1):
        try:
            response = sess.get(url, timeout=timeout, headers={"Accept": "text/html,application/xhtml+xml"})
            response.raise_for_status()
            return parse_series_search_html(response.text, ticker)
        except Exception as exc:
            errors.append(f"attempt {attempt}: {exc}")
            if attempt < max(1, int(retries)):
                sleep(0.75 * attempt)
    raise RuntimeError("; ".join(errors[-2:]) or f"SEC fund search unavailable for {ticker}")


def _load_market_rows(stocks_path=STOCKS_PATH):
    payload = json.loads(Path(stocks_path).read_text(encoding="utf-8"))
    return [r for r in payload.get("stocks", []) if isinstance(r, dict)]


def unresolved_series_candidates(rows):
    out = []
    for row in rows:
        if str(row.get("quote_type") or "").strip():
            continue
        if str(row.get("region") or "").strip().upper() not in US_REGIONS:
            continue
        ticker = _normal_ticker(row.get("ticker"))
        if ticker and "." not in ticker:
            out.append(ticker)
    return sorted(set(out))


def resolve_via_series(rows, session=None, delay=0.16, max_candidates=400):
    """Resolve only unresolved candidates; no-match remains unresolved."""
    candidates = unresolved_series_candidates(rows)[:max_candidates]
    mapping = {}
    errors = []
    attempted = 0
    for ticker in candidates:
        attempted += 1
        try:
            item = fetch_series_exact(ticker, session=session)
            if item:
                mapping[ticker] = item
        except Exception as exc:
            errors.append({"ticker": ticker, "error": str(exc)[:240]})
        if delay:
            time.sleep(delay)
    return mapping, {
        "attempted": attempted,
        "matched": len(mapping),
        "errors": len(errors),
        "error_examples": errors[:20],
    }


def refresh_snapshot(session=None, stocks_path=STOCKS_PATH):
    """Prefer full bulk map; otherwise use SEC exact series search."""
    direct_error = None
    try:
        mapping = fetch_remote(session=session)
        write_snapshot(mapping, source=SEC_FUND_TICKERS, transport="direct_sec", scope="complete")
        return mapping, {
            "state": "remote",
            "source": SEC_FUND_TICKERS,
            "transport": "direct_sec",
            "scope": "complete",
            "series_search": None,
        }
    except Exception as exc:
        direct_error = str(exc)

    rows = _load_market_rows(stocks_path)
    try:
        sentinel = fetch_series_exact(SERIES_SENTINEL, session=session)
        if not sentinel:
            raise RuntimeError(f"SEC series sentinel {SERIES_SENTINEL} returned no exact fund match")
        mapping, series_diag = resolve_via_series(rows, session=session)
        if mapping:
            write_snapshot(mapping, source=SEC_FUND_SEARCH, transport="sec_series_search", scope="unresolved_exact_search")
        return mapping, {
            "state": "remote_series_search",
            "source": SEC_FUND_SEARCH,
            "transport": "sec_series_search",
            "scope": "unresolved_exact_search",
            "bulk_error": direct_error,
            "series_sentinel": {"ticker": SERIES_SENTINEL, "matched": True, "identity": sentinel},
            "series_search": series_diag,
        }
    except Exception as series_error:
        cached = read_snapshot()
        if cached:
            payload = cached[1]
            return cached[0], {
                "state": "snapshot_fallback",
                "source": payload.get("source") or SEC_FUND_TICKERS,
                "transport": payload.get("transport") or "unknown",
                "scope": payload.get("scope") or "unknown",
                "bulk_error": direct_error,
                "series_error": str(series_error),
                "series_search": None,
            }
        return {}, {
            "state": "unavailable",
            "source": SEC_FUND_TICKERS,
            "transport": None,
            "scope": None,
            "bulk_error": direct_error,
            "series_error": str(series_error),
            "series_search": None,
        }


def build_audit(mapping, source_meta, stocks_path=STOCKS_PATH):
    try:
        rows = _load_market_rows(stocks_path)
    except Exception as exc:
        rows = []
        source_meta = {**dict(source_meta or {}), "stocks_error": str(exc)}

    unresolved_matches = []
    explicit_equity_conflicts = []
    explicit_non_equity_matches = []
    all_matches = 0
    for row in rows:
        ticker = _normal_ticker(row.get("ticker"))
        if not ticker or ticker not in mapping:
            continue
        all_matches += 1
        quote_type = str(row.get("quote_type") or "").strip().upper()
        item = {
            "ticker": ticker,
            "name": row.get("name"),
            "region": row.get("region"),
            "reported_quote_type": quote_type or None,
            "coverage_pct": row.get("data_coverage_pct"),
            "pipeline_status": row.get("pipeline_status"),
            "sec_fund_identity": mapping[ticker],
        }
        if not quote_type:
            unresolved_matches.append(item)
        elif quote_type in {"ETF", "FUND", "MUTUALFUND"}:
            explicit_non_equity_matches.append(item)
        else:
            explicit_equity_conflicts.append(item)

    source_meta = dict(source_meta or {})
    series_diag = source_meta.get("series_search") or {}
    audit = {
        "schema_version": 2,
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "source": source_meta.get("source") or SEC_FUND_TICKERS,
        "source_state": source_meta.get("state") or "unknown",
        "transport": source_meta.get("transport"),
        "identity_scope": source_meta.get("scope"),
        "sec_fund_identity_count": len(mapping),
        "sec_fund_ticker_count": len(mapping),
        "market_rows_checked": len(rows),
        "market_rows_matching_sec_fund_map": all_matches,
        "unresolved_rows_confirmed_as_registered_funds": len(unresolved_matches),
        "explicit_non_equity_rows_confirmed": len(explicit_non_equity_matches),
        "explicit_equity_type_conflicts": len(explicit_equity_conflicts),
        "series_search_attempted": series_diag.get("attempted", 0),
        "series_search_matched": series_diag.get("matched", 0),
        "series_search_errors": series_diag.get("errors", 0),
        "series_search_error_examples": series_diag.get("error_examples", []),
        "source_diagnostics": source_meta,
        "unresolved_examples": unresolved_matches[:200],
        "type_conflict_examples": explicit_equity_conflicts[:100],
    }
    AUDIT_PATH.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        "SEC fund identity audit: "
        f"state={audit['source_state']}; scope={audit['identity_scope']}; "
        f"{len(mapping)} confirmed fund identities; "
        f"{len(unresolved_matches)} unresolved matches; "
        f"{len(explicit_equity_conflicts)} explicit type conflicts"
    )
    return audit


def main():
    mapping, meta = refresh_snapshot()
    build_audit(mapping, meta)


if __name__ == "__main__":
    main()
