"""Small SEC connectivity probe and runtime guard for Vestra.

The market pipeline already validates and seeds an exact SEC ticker->CIK snapshot.
This module performs deterministic probes so GitHub Actions logs show whether the
runner can reach:

- per-company CompanyFacts and Submissions APIs;
- the official nightly CompanyFacts and Submissions bulk archives;
- immutable EDGAR Archives index/filing/XBRL paths that can support a fallback
  when data.sec.gov and the bulk ZIPs are blocked.

Bulk ZIP probes keep their one-byte Range request. EDGAR Archives probes use a
normal streamed GET and close the response immediately without consuming the
body, matching the request shape already proven by Vestra's SEC filing fetchers.
The probe never mutates market data and never retries through proxies or mirrors.
When every tested per-company SEC API endpoint returns the same explicit HTTP 403,
the CLI writes an empty SEC_USER_AGENT to GITHUB_ENV so the following pipeline
step skips the existing CompanyFacts network lane. EDGAR Archives diagnostics are
observational only and do not alter that guard. Score/Risk Gate semantics are
never changed.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import requests

from sec_enrich import TICKER_MAP_SNAPSHOT, _read_ticker_snapshot

BASE = "https://data.sec.gov"
SENTINELS = ("AAPL", "MSFT", "NVDA")
BULK_ENDPOINTS = {
    "companyfacts_zip": "https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip",
    "submissions_zip": "https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip",
}
ARCHIVE_ENDPOINTS = {
    "quarter_master_index": "https://www.sec.gov/Archives/edgar/full-index/2026/QTR3/master.idx",
    "aapl_10q_filing_index": "https://www.sec.gov/Archives/edgar/data/320193/000032019326000020/0000320193-26-000020-index.htm",
    "aapl_10q_xbrl_instance": "https://www.sec.gov/Archives/edgar/data/320193/000032019326000020/aapl-20260627_htm.xml",
}


def _content_type(response):
    headers = getattr(response, "headers", {}) or {}
    return str(headers.get("content-type") or headers.get("Content-Type") or "").split(";", 1)[0].strip().lower() or None


def _probe_response(response, family: str):
    status = int(getattr(response, "status_code", 0) or 0)
    result = {
        "status": status,
        "ok": 200 <= status < 300,
        "content_type": _content_type(response),
        "json_valid": False,
        "payload_present": False,
    }
    if not result["ok"]:
        return result
    try:
        payload = response.json()
    except Exception:
        return result
    result["json_valid"] = isinstance(payload, dict)
    if not isinstance(payload, dict):
        return result
    if family == "companyfacts":
        result["payload_present"] = isinstance(payload.get("facts"), dict) and bool(payload.get("facts"))
    elif family == "submissions":
        filings = payload.get("filings")
        result["payload_present"] = isinstance(filings, dict) and isinstance(filings.get("recent"), dict)
    return result


def _stream_result(response):
    status = int(getattr(response, "status_code", 0) or 0)
    headers = getattr(response, "headers", {}) or {}
    result = {
        "status": status,
        "ok": status in (200, 206),
        "content_type": _content_type(response),
        "content_length": headers.get("content-length") or headers.get("Content-Length"),
        "content_range": headers.get("content-range") or headers.get("Content-Range"),
        "accept_ranges": headers.get("accept-ranges") or headers.get("Accept-Ranges"),
    }
    close = getattr(response, "close", None)
    if callable(close):
        close()
    return result


def _stream_error(exc):
    return {
        "status": 0,
        "ok": False,
        "content_type": None,
        "content_length": None,
        "content_range": None,
        "accept_ranges": None,
        "error": type(exc).__name__,
    }


def _probe_range(session, url, *, accept="*/*"):
    try:
        response = session.get(
            url,
            timeout=20,
            headers={"Range": "bytes=0-0", "Accept": accept},
            stream=True,
        )
        return _stream_result(response)
    except Exception as exc:
        return _stream_error(exc)


def _probe_stream_get(session, url, *, accept="*/*"):
    """Probe normal GET semantics without downloading the streamed response body."""
    try:
        response = session.get(
            url,
            timeout=20,
            headers={"Accept": accept},
            stream=True,
        )
        return _stream_result(response)
    except Exception as exc:
        return _stream_error(exc)


def _probe_bulk(session, url):
    return _probe_range(session, url, accept="application/zip, application/octet-stream, */*")


def _runtime_sec_blocked(report):
    """Return True only for a broad, explicit SEC API 403 across all API probes."""
    sentinels = report.get("sentinels") if isinstance(report, dict) else None
    if not isinstance(sentinels, dict) or not sentinels:
        return False
    statuses = []
    for row in sentinels.values():
        if not isinstance(row, dict) or not row.get("cik"):
            return False
        for family in ("companyfacts", "submissions"):
            outcome = row.get(family)
            if not isinstance(outcome, dict):
                return False
            statuses.append(int(outcome.get("status") or 0))
    summary = report.get("summary") or {}
    return bool(statuses) and len(statuses) >= 4 and all(status == 403 for status in statuses) and int(summary.get("http_ok") or 0) == 0


def apply_runtime_guard(report, env_path=None):
    """Disable the current CompanyFacts lane for subsequent Actions steps when blocked."""
    blocked = _runtime_sec_blocked(report)
    path = env_path if env_path is not None else os.getenv("GITHUB_ENV")
    if blocked and path:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as handle:
            handle.write("SEC_USER_AGENT=\n")
        print("SEC runtime guard: upstream returned 403 for all API sentinels; SEC enrichment disabled for subsequent steps")
    return blocked


def probe(session=None, snapshot_path=TICKER_MAP_SNAPSHOT, sentinels=SENTINELS, archive_endpoints=ARCHIVE_ENDPOINTS):
    cached = _read_ticker_snapshot(snapshot_path)
    ua = os.getenv("SEC_USER_AGENT", "Vestra/4.0 (+https://github.com/possn/Vestra)").strip()
    session = session or requests.Session()
    if hasattr(session, "headers"):
        session.headers.update({
            "User-Agent": ua,
            "Accept-Encoding": "gzip, deflate",
            "Accept": "application/json",
        })

    report = {
        "snapshot_available": bool(cached),
        "sentinels": {},
        "bulk": {},
        "archives": {},
        "summary": {
            "requests": 0,
            "http_ok": 0,
            "payload_ok": 0,
            "bulk_requests": 0,
            "bulk_ok": 0,
            "archive_requests": 0,
            "archive_ok": 0,
        },
    }

    if cached:
        cmap, snapshot = cached
        report["snapshot_count"] = len(cmap)
        report["snapshot_source"] = snapshot.get("source")
        for ticker in sentinels:
            cik = cmap.get(str(ticker).upper())
            row = {"cik": cik, "companyfacts": None, "submissions": None}
            report["sentinels"][str(ticker).upper()] = row
            if not cik:
                continue
            padded = f"{int(cik):010d}"
            endpoints = (
                ("companyfacts", f"{BASE}/api/xbrl/companyfacts/CIK{padded}.json"),
                ("submissions", f"{BASE}/submissions/CIK{padded}.json"),
            )
            for family, url in endpoints:
                report["summary"]["requests"] += 1
                try:
                    response = session.get(url, timeout=20)
                    outcome = _probe_response(response, family)
                except Exception as exc:
                    outcome = {
                        "status": 0,
                        "ok": False,
                        "content_type": None,
                        "json_valid": False,
                        "payload_present": False,
                        "error": type(exc).__name__,
                    }
                row[family] = outcome
                if outcome.get("ok"):
                    report["summary"]["http_ok"] += 1
                if outcome.get("payload_present"):
                    report["summary"]["payload_ok"] += 1

    for name, url in BULK_ENDPOINTS.items():
        report["summary"]["bulk_requests"] += 1
        outcome = _probe_bulk(session, url)
        report["bulk"][name] = outcome
        if outcome.get("ok"):
            report["summary"]["bulk_ok"] += 1

    for name, url in (archive_endpoints or {}).items():
        report["summary"]["archive_requests"] += 1
        outcome = _probe_stream_get(session, url, accept="text/plain, text/html, application/xml, text/xml, */*")
        report["archives"][name] = outcome
        if outcome.get("ok"):
            report["summary"]["archive_ok"] += 1

    print("SEC endpoint probe: " + json.dumps(report, sort_keys=True, separators=(",", ":")))
    return report


def main():
    report = probe()
    apply_runtime_guard(report)


if __name__ == "__main__":
    main()
