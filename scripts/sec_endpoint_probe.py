"""Small read-only probe for SEC post-CIK endpoints used by Vestra.

The market pipeline already validates and seeds an exact SEC ticker->CIK snapshot.
This module performs a tiny deterministic probe after that seed and before the
heavy pipeline so GitHub Actions logs show whether the runner can actually reach
the two downstream SEC data families used by Vestra:

- CompanyFacts (fundamental enrichment)
- Submissions (capital-structure risk scanner)

It never mutates market data, never retries through proxies/mirrors, and never
changes Score/Risk Gate semantics. Failure of individual probe requests is
reported as diagnostics rather than treated as market evidence.
"""
from __future__ import annotations

import json
import os

import requests

from sec_enrich import TICKER_MAP_SNAPSHOT, _read_ticker_snapshot

BASE = "https://data.sec.gov"
SENTINELS = ("AAPL", "MSFT", "NVDA")


def _probe_response(response, family: str):
    status = int(getattr(response, "status_code", 0) or 0)
    headers = getattr(response, "headers", {}) or {}
    content_type = str(headers.get("content-type") or headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
    result = {
        "status": status,
        "ok": 200 <= status < 300,
        "content_type": content_type or None,
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


def probe(session=None, snapshot_path=TICKER_MAP_SNAPSHOT, sentinels=SENTINELS):
    cached = _read_ticker_snapshot(snapshot_path)
    if not cached:
        report = {
            "snapshot_available": False,
            "sentinels": {},
            "summary": {"requests": 0, "http_ok": 0, "payload_ok": 0},
        }
        print("SEC endpoint probe: " + json.dumps(report, sort_keys=True, separators=(",", ":")))
        return report

    cmap, snapshot = cached
    ua = os.getenv("SEC_USER_AGENT", "Vestra/4.0 (+https://github.com/possn/Vestra)").strip()
    session = session or requests.Session()
    if hasattr(session, "headers"):
        session.headers.update({
            "User-Agent": ua,
            "Accept-Encoding": "gzip, deflate",
            "Accept": "application/json",
        })

    report = {
        "snapshot_available": True,
        "snapshot_count": len(cmap),
        "snapshot_source": snapshot.get("source"),
        "sentinels": {},
        "summary": {"requests": 0, "http_ok": 0, "payload_ok": 0},
    }

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

    print("SEC endpoint probe: " + json.dumps(report, sort_keys=True, separators=(",", ":")))
    return report


def main():
    probe()


if __name__ == "__main__":
    main()
