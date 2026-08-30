#!/usr/bin/env python3
"""Verify a deployed Vestra Cloudflare Worker against the source contract.

Usage:
  python scripts/verify_worker_deployment.py --url https://example.workers.dev

The script is deliberately read-only. It performs GET requests only and never
changes Cloudflare state.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import requests


DEFAULT_ORIGIN = "https://possn.github.io"
DEFAULT_TICKERS = ["MSFT", "AAPL"]
ROOT = Path(__file__).resolve().parents[1]
WORKER_SOURCE = ROOT / "worker.js"


@dataclass
class Check:
    name: str
    ok: bool
    detail: str


def source_worker_contract() -> dict[str, Any]:
    text = WORKER_SOURCE.read_text(encoding="utf-8")
    version = re.search(r"Versão\s+([0-9.]+)", text)
    quote_ttl = re.search(r"const QUOTE_CACHE_TTL\s*=\s*(\d+)", text)
    market_ttl = re.search(r"const MARKET_CACHE_TTL\s*=\s*(\d+)", text)
    return {
        "version": version.group(1) if version else None,
        "quote_cache_ttl_seconds": int(quote_ttl.group(1)) if quote_ttl else None,
        "market_cache_ttl_seconds": int(market_ttl.group(1)) if market_ttl else None,
    }


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


def market_summary(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    return {
        "ticker": payload.get("ticker"),
        "current_price": payload.get("current_price"),
        "_cached": payload.get("_cached"),
        "updated": payload.get("updated"),
        "quote_updated": payload.get("quote_updated"),
        "market_cap": payload.get("market_cap"),
        "forward_pe": payload.get("forward_pe"),
        "fcf_yield": payload.get("fcf_yield"),
    }


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
    session.headers.update({"User-Agent": "Vestra-Worker-Audit/1.1"})

    checks: list[Check] = []
    report: dict[str, Any] = {"worker": base, "origin": args.origin, "checks": []}
    contract = source_worker_contract()
    report["source_contract"] = contract

    try:
        root_resp, root, root_ms = get_json(session, base + "/", origin=args.origin, timeout=args.timeout)
        root_ok = root_resp.ok and isinstance(root, dict)
        checks.append(Check("GET /", root_ok, f"HTTP {root_resp.status_code}, {root_ms} ms"))
        checks.append(cors_check(root_resp, args.origin))
        report["root"] = root
    except Exception as exc:
        checks.append(Check("GET /", False, repr(exc)))

    try:
        health_resp, health, health_ms = get_json(session, base + "/health", origin=args.origin, timeout=args.timeout)
        if health_resp.status_code == 404:
            checks.append(Check("GET /health", False, "not implemented (404)"))
        else:
            health_ok = health_resp.ok and isinstance(health, dict)
            checks.append(Check("GET /health", health_ok, f"HTTP {health_resp.status_code}, {health_ms} ms"))
            report["health"] = health
            if health_ok:
                checks.append(Check(
                    "deployed/source Worker version",
                    health.get("version") == contract.get("version"),
                    f"deployed={health.get('version')!r}, source={contract.get('version')!r}",
                ))
                for key, label in (
                    ("quote_cache_ttl_seconds", "quote cache TTL"),
                    ("market_cache_ttl_seconds", "market cache TTL"),
                ):
                    expected = contract.get(key)
                    checks.append(Check(
                        label,
                        health.get(key) == expected,
                        f"deployed={health.get(key)!r}, source={expected!r}",
                    ))
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
        resp1, market1, elapsed1 = get_json(session, url, origin=args.origin, timeout=args.timeout)
        time.sleep(1.0)
        resp2, market2, elapsed2 = get_json(session, url, origin=args.origin, timeout=args.timeout)
        ok = resp1.ok and resp2.ok and isinstance(market1, dict) and isinstance(market2, dict)
        checks.append(Check(f"GET /market {probe}", ok, f"HTTP {resp2.status_code}, {elapsed2} ms"))

        quote = single_quotes.get(probe.upper()) or {}
        q_price = float(quote["price"]) if finite_positive(quote.get("price")) else None
        m_price = float(market2["current_price"]) if isinstance(market2, dict) and finite_positive(market2.get("current_price")) else None
        if q_price is not None and m_price is not None:
            rel = abs(q_price - m_price) / max(abs(q_price), abs(m_price), 1e-9)
            checks.append(Check(
                f"quote/market price equivalence {probe.upper()}",
                rel <= 0.01,
                f"quote={q_price}, market={m_price}, rel_diff={rel:.4%}",
            ))
        else:
            checks.append(Check(f"quote/market price equivalence {probe.upper()}", False, "missing positive price"))

        cache_hit = isinstance(market2, dict) and market2.get("_cached") is True
        quote_updated = market2.get("quote_updated") if isinstance(market2, dict) else None
        checks.append(Check(
            "cached /market fresh quote overlay",
            cache_hit and bool(quote_updated),
            f"cached={cache_hit}, quote_updated={quote_updated!r}",
        ))
        report["market_probe"] = {
            "first": market_summary(market1),
            "second": market_summary(market2),
            "first_ms": elapsed1,
            "second_ms": elapsed2,
        }
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
        checks.append(Check(
            "cache diagnostics exposed",
            isinstance(q2, dict) and "updated" in q2,
            json.dumps(cache_signal),
        ))
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
