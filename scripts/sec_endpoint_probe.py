"""Small read-only probe for SEC endpoints used by Vestra.

The market pipeline already validates and seeds an exact SEC ticker->CIK snapshot.
This module performs deterministic probes so GitHub Actions logs show whether the
runner can reach:

- per-company CompanyFacts and Submissions APIs;
- the official nightly CompanyFacts and Submissions bulk archives.

Bulk probes use a streaming GET with a one-byte Range request and never consume
the ZIP body. The module never mutates market data, never retries through proxies
or mirrors, and never changes Score/Risk Gate semantics.
"""
from __future__ import annotations

import json
import os

import requests

from sec_enrich import TICKER_MAP_SNAPSHOT, _read_ticker_snapshot

BASE = "https://data.sec.gov"
SENTINELS = ("AAPL", "MSFT", "NVDA")
BULK_ENDPOINTS = {
    "companyfacts_zip": "https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip",
    "submissions_zip": "https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip",
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


def _probe_bulk(session, url):
    try:
        response = session.get(
            url,
            timeout=20,
            headers={"Range": "bytes=0-0", "Accept": "application/zip, application/octet-stream, */*"},
            stream=True,
        )
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
    except Exception as exc:
        return {
            "status": 0,
            "ok": False,
            "content_type": None,
            "content_length": None,
            "content_range": None,
            "accept_ranges": None,
            "error": type(exc).__name__,
        }


def probe(session=None, snapshot_path=TICKER_MAP_SNAPSHOT, sentinels=SENTINELS):
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
        "summary": {"requests": 0, "http_ok": 0, "payload_ok": 0, "bulk_requests": 0, "bulk_ok": 0},
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

    print("SEC endpoint probe: " + json.dumps(report, sort_keys=True, separators=(",", ":")))
    return report


def main():
    probe()


if __name__ == "__main__":
    main()
