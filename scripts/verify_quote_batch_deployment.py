#!/usr/bin/env python3
"""Fail closed unless production exposes the quote-batch contract in source."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlencode

import requests

ROOT = Path(__file__).resolve().parents[1]
ROUTER = ROOT / "worker-router.js"
DEFAULT_ORIGIN = "https://possn.github.io"
PROBE_TICKERS = ["MSFT", "AAPL", "BEN", "PNR", "RIO.L", "HEI.DE", "VUAA.DE", "NEAR-USD"]


def source_contract() -> dict:
    text = ROUTER.read_text(encoding="utf-8")
    transport = re.search(r"quote_batch_transport:'([^']+)'", text)
    chunk = re.search(r"quote_batch_chunk_size:(\d+)", text)
    fallback = re.search(r"const BATCH_CHART_FALLBACK_CONCURRENCY\s*=\s*(\d+)", text)
    if not transport:
        raise RuntimeError("worker-router.js does not expose quote_batch_transport")
    return {
        "quote_batch_transport": transport.group(1),
        "quote_batch_chunk_size": int(chunk.group(1)) if chunk else None,
        "quote_batch_chart_fallback_concurrency": int(fallback.group(1)) if fallback else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--origin", default=DEFAULT_ORIGIN)
    parser.add_argument("--timeout", type=float, default=15.0)
    args = parser.parse_args()

    base = args.url.rstrip("/")
    expected = source_contract()
    session = requests.Session()
    session.headers.update({"User-Agent": "Vestra-Quote-Batch-Deployment-Audit/1.0"})
    headers = {"Accept": "application/json", "Origin": args.origin}

    failures = []
    try:
        resp = session.get(base + "/health", headers=headers, timeout=args.timeout)
        health = resp.json() if resp.ok else {}
    except Exception as exc:
        print(json.dumps({"ok": False, "error": repr(exc), "expected": expected}, ensure_ascii=False))
        return 1

    for key, value in expected.items():
        if value is None:
            continue
        actual = health.get(key)
        if actual != value:
            failures.append(f"{key}: deployed={actual!r}, source={value!r}")

    batch = None
    elapsed_ms = None
    if not failures:
        try:
            import time
            started = time.perf_counter()
            resp = session.get(
                base + "/quotes?" + urlencode({"tickers": ",".join(PROBE_TICKERS)}),
                headers=headers,
                timeout=args.timeout,
            )
            elapsed_ms = round((time.perf_counter() - started) * 1000)
            batch = resp.json() if resp.ok else None
            if not resp.ok or not isinstance(batch, dict):
                failures.append(f"mixed batch HTTP {resp.status_code}")
            else:
                missing_keys = [ticker for ticker in PROBE_TICKERS if ticker not in batch]
                if missing_keys:
                    failures.append("mixed batch missing keys: " + ", ".join(missing_keys))
        except Exception as exc:
            failures.append(f"mixed batch transport error: {exc!r}")

    report = {
        "ok": not failures,
        "worker": base,
        "expected": expected,
        "deployed": {
            "quote_batch_transport": health.get("quote_batch_transport"),
            "quote_batch_chunk_size": health.get("quote_batch_chunk_size"),
            "quote_batch_chart_fallback_concurrency": health.get("quote_batch_chart_fallback_concurrency"),
        },
        "probe_tickers": PROBE_TICKERS,
        "batch_elapsed_ms": elapsed_ms,
        "failures": failures,
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
