#!/usr/bin/env python3
"""Verify a deployed Vestra Cloudflare Worker against the source contract.

Usage:
  python scripts/verify_worker_deployment.py --url https://example.workers.dev

The script is deliberately read-only. It performs GET/OPTIONS requests only and
never changes Cloudflare state.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import requests


DEFAULT_ORIGIN = "https://possn.github.io"
DEFAULT_TICKERS = ["MSFT", "AAPL"]


@dataclass
class Check:
    name: str
    ok: bool
    detail: str


def clean_base(url: str) -> str:
    return url.strip().rstrip("/")


def get_json(session: requests.Session, url: str, *, origin: str | None = None, timeout: float = 12.0):
    headers = {"Accept": "application/json"}
    if origin:
        headers["Origin"] = origin
    started = time.perf_counter()
    resp = session.get(url, headers=headers, timeout=timeout)
    elapsed_ms = round((time.perf_counter() - started) * 1000)
    try:
        payload = resp.json()
    except Exception:
        payload = None
    return resp, payload, elapsed_ms


def finite_positive(value: Any) -> bool:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(v) and v > 0


def cors_check(resp: requests.Response, origin: str) -> Check:
    allow = resp.headers.get("Access-Control-Allow-Origin", "")
    vary = resp.headers.get("Vary", "")
    ok = allow == origin and "origin" in vary.lower()
    return Check(
        "CORS production origin",
        ok,
        f"allow-origin={allow!r}, vary={vary!r}",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True, help="Worker base URL")
    parser.add_argument("--origin", default=DEFAULT_ORIGIN)
    parser.add_argument("--ticker", action="append", dest="tickers")
    parser.add_argument("--timeout", type=float, default=12.0)
    args = parser.parse_args()

    base = clean_base(args.url)
    tickers = args.tickers or DEFAULT_TICKERS
    session = requests.Session()
    session.headers.update({"User-Agent": "Vestra-Worker-Audit/1.0"})

    checks: list[Check] = []
    report: dict[str, Any] = {"worker": base, "origin": args.origin, "checks": []}

    try:
        root_resp, root, root_ms = get_json(session, base + "/", origin=args.origin, timeout=args.timeout)
        root_ok = root_resp.ok and isinstance(root, dict)
        checks.append(Check("GET /", root_ok, f"HTTP {root_resp.status_code}, {root_ms} ms"))
        checks.append(cors_check(root_resp, args.origin))
        report["root"] = root
    except Exception as exc:
        checks.append(Check("GET /", False, repr(exc)))
        root = None

    try:
        health_resp, health, health_ms = get_json(session, base + "/health", origin=args.origin, timeout=args.timeout)
        if health_resp.status_code == 404:
            checks.append(Check("GET /health", False, "not implemented (404)"))
        else:
            health_ok = health_resp.ok and isinstance(health, dict)
            checks.append(Check("GET /health", health_ok, f"HTTP {health_resp.status_code}, {health_ms} ms"))
            report["health"] = health
    except Exception as exc:
        checks.append(Check("GET /health", False, repr(exc)))

    single_quotes: dict[str, dict[str, Any]] = {}
    for ticker in tickers:
        try:
            url = f"{base}/quote?{urlencode({'ticker': ticker})}"
            resp, payload, elapsed = get_json(session, url, origin=args.origin, timeout=args.timeout)
            ok = resp.ok and isinstance(payload, dict) and finite_positive(payload.get("price"))
            checks.append(Check(f"GET /quote {ticker}", ok, f"HTTP {resp.status_code}, {elapsed} ms"))
            if isinstance(payload, dict):
                single_quotes[ticker.upper()] = payload
        except Exception as exc:
            checks.append(Check(f"GET /quote {ticker}", False, repr(exc)))

    try:
        joined = ",".join(tickers)
        url = f"{base}/quotes?{urlencode({'tickers': joined})}"
        resp, batch, elapsed = get_json(session, url, origin=args.origin, timeout=args.timeout)
        batch_ok = resp.ok and isinstance(batch, dict)
        checks.append(Check("GET /quotes batch", batch_ok, f"HTTP {resp.status_code}, {elapsed} ms"))
        if isinstance(batch, dict):
            report["batch"] = batch
            for ticker in tickers:
                tk = ticker.upper()
                one = single_quotes.get(tk) or {}
                row = batch.get(tk) if isinstance(batch.get(tk), dict) else {}
                if finite_positive(one.get("price")) and finite_positive(row.get("price")):
                    p1 = float(one["price"])
                    p2 = float(row["price"])
                    rel = abs(p1 - p2) / max(abs(p1), abs(p2), 1e-9)
                    checks.append(Check(
                        f"single/batch equivalence {tk}",
                        rel <= 0.01,
                        f"single={p1}, batch={p2}, rel_diff={rel:.4%}",
                    ))
                else:
                    checks.append(Check(f"single/batch equivalence {tk}", False, "missing positive price"))
    except Exception as exc:
        checks.append(Check("GET /quotes batch", False, repr(exc)))

    probe = tickers[0]
    try:
        url = f"{base}/market?{urlencode({'ticker': probe})}"
        resp, payload, elapsed = get_json(session, url, origin=args.origin, timeout=args.timeout)
        ok = resp.ok and isinstance(payload, dict)
        checks.append(Check(f"GET /market {probe}", ok, f"HTTP {resp.status_code}, {elapsed} ms"))
    except Exception as exc:
        checks.append(Check(f"GET /market {probe}", False, repr(exc)))

    try:
        bad_origin = "https://example.invalid"
        resp, _, _ = get_json(session, base + "/", origin=bad_origin, timeout=args.timeout)
        allow = resp.headers.get("Access-Control-Allow-Origin", "")
        ok = allow not in {bad_origin, "*"}
        checks.append(Check("CORS unrelated origin rejected", ok, f"allow-origin={allow!r}"))
    except Exception as exc:
        checks.append(Check("CORS unrelated origin rejected", False, repr(exc)))

    try:
        url = f"{base}/quote?{urlencode({'ticker': probe})}"
        r1, q1, _ = get_json(session, url, origin=args.origin, timeout=args.timeout)
        time.sleep(1.0)
        r2, q2, _ = get_json(session, url, origin=args.origin, timeout=args.timeout)
        cache_signal = {
            "first_cached": q1.get("_cached") if isinstance(q1, dict) else None,
            "second_cached": q2.get("_cached") if isinstance(q2, dict) else None,
            "first_updated": q1.get("updated") if isinstance(q1, dict) else None,
            "second_updated": q2.get("updated") if isinstance(q2, dict) else None,
            "cache_control_1": r1.headers.get("Cache-Control"),
            "cache_control_2": r2.headers.get("Cache-Control"),
        }
        report["cache_probe"] = cache_signal
        checks.append(Check("cache diagnostics exposed", isinstance(q2, dict) and "updated" in q2, json.dumps(cache_signal)))
    except Exception as exc:
        checks.append(Check("cache diagnostics exposed", False, repr(exc)))

    failures = 0
    for check in checks:
        status = "PASS" if check.ok else "FAIL"
        if not check.ok:
            failures += 1
        print(f"[{status}] {check.name}: {check.detail}")
        report["checks"].append({"name": check.name, "ok": check.ok, "detail": check.detail})

    print("\n--- JSON REPORT ---")
    print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
