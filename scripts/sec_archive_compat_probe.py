"""Diagnostic: reproduce Vestra's historically successful SEC Archives request shape.

This probe is deliberately isolated from the market pipeline. It uses the same
identifying User-Agent, retry policy, persistent Session and request cadence as
scripts/insiders.py, and tests immutable EDGAR Archives objects before any other
SEC requests are made by the workflow. It does not write market data or alter the
SEC runtime guard.
"""
from __future__ import annotations

import json
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

USER_AGENT = "Finscanner research-tool finscanner-app@proton.me"
ENDPOINTS = {
    "quarter_master_index": "https://www.sec.gov/Archives/edgar/full-index/2026/QTR3/master.idx",
    "aapl_10q_filing_index": "https://www.sec.gov/Archives/edgar/data/320193/000032019326000020/0000320193-26-000020-index.htm",
    "aapl_10q_xbrl_instance": "https://www.sec.gov/Archives/edgar/data/320193/000032019326000020/aapl-20260627_htm.xml",
}


def build_session():
    session = requests.Session()
    retry = Retry(
        total=2,
        connect=2,
        read=2,
        status=2,
        backoff_factor=0.8,
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


def probe(session=None, endpoints=ENDPOINTS, sleeper=time.sleep):
    session = session or build_session()
    results = {}
    for index, (name, url) in enumerate((endpoints or {}).items()):
        if index:
            sleeper(0.2)
        try:
            response = session.get(url, timeout=25, stream=True)
            status = int(getattr(response, "status_code", 0) or 0)
            headers = getattr(response, "headers", {}) or {}
            results[name] = {
                "status": status,
                "ok": 200 <= status < 300,
                "content_type": str(headers.get("content-type") or headers.get("Content-Type") or "").split(";", 1)[0].strip().lower() or None,
                "content_length": headers.get("content-length") or headers.get("Content-Length"),
            }
            close = getattr(response, "close", None)
            if callable(close):
                close()
        except Exception as exc:
            response = getattr(exc, "response", None)
            results[name] = {
                "status": int(getattr(response, "status_code", 0) or 0),
                "ok": False,
                "content_type": None,
                "content_length": None,
                "error": type(exc).__name__,
            }
    report = {
        "request_profile": "insiders_exact_v1",
        "user_agent": USER_AGENT,
        "requests": len(results),
        "http_ok": sum(1 for row in results.values() if row.get("ok")),
        "results": results,
    }
    print("SEC Archives compatibility probe: " + json.dumps(report, sort_keys=True, separators=(",", ":")))
    return report


def main():
    probe()


if __name__ == "__main__":
    main()
