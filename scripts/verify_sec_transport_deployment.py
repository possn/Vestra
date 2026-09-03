#!/usr/bin/env python3
"""Read-only verification of Vestra's experimental SEC transport."""
from __future__ import annotations

import argparse
import json
import sys
from urllib.parse import urlencode

import requests


def clean_base(url: str) -> str:
    return url.strip().rstrip("/")


def compact_error_payload(payload):
    if not isinstance(payload, dict):
        return None
    allowed = ("error", "upstream_status", "error_type")
    return {key: payload.get(key) for key in allowed if payload.get(key) is not None} or None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args()

    base = clean_base(args.url)
    session = requests.Session()
    session.headers.update({"Accept": "application/json", "User-Agent": "Vestra-SEC-Transport-Audit/1.2"})
    failures = []
    degraded = []

    try:
        health = session.get(base + "/health", timeout=args.timeout)
        payload = health.json()
        capabilities = payload.get("capabilities") if isinstance(payload, dict) else []
        experimental = payload.get("experimental_capabilities") if isinstance(payload, dict) else []
        sec_meta = payload.get("sec_transport") if isinstance(payload, dict) else None
        ok = (
            health.ok
            and isinstance(capabilities, list)
            and "sec_transport" not in capabilities
            and isinstance(experimental, list)
            and "sec_transport" in experimental
            and isinstance(sec_meta, dict)
            and sec_meta.get("status") == "experimental_not_in_pipeline"
        )
        print(f"[{'PASS' if ok else 'FAIL'}] health SEC transport is experimental, not operational: HTTP {health.status_code}")
        if not ok:
            failures.append("health semantics")
    except Exception as exc:
        print(f"[FAIL] health SEC transport semantics: {exc!r}")
        failures.append("health exception")

    probes = (
        ("companyfacts", 320193, "facts"),
        ("submissions", 320193, "filings"),
    )
    for family, cik, required_key in probes:
        url = f"{base}/sec/{family}?{urlencode({'cik': cik})}"
        try:
            response = session.get(url, timeout=args.timeout)
            try:
                payload = response.json()
            except Exception:
                payload = None
            valid = response.ok and isinstance(payload, dict) and isinstance(payload.get(required_key), dict)
            source = response.headers.get("X-Vestra-Sec-Source")
            cache = response.headers.get("X-Vestra-Sec-Cache")
            diagnostic = compact_error_payload(payload)
            live_ok = valid and source == "sec.gov" and cache in {"hit", "miss"}
            known_block = (
                response.status_code == 502
                and isinstance(diagnostic, dict)
                and diagnostic.get("error") == "SEC upstream indisponível"
                and diagnostic.get("upstream_status") == 403
            )
            state = "PASS" if live_ok else ("WARN" if known_block else "FAIL")
            print(
                f"[{state}] GET /sec/{family}: HTTP {response.status_code}, "
                f"source={source!r}, cache={cache!r}, "
                f"diagnostic={json.dumps(diagnostic, ensure_ascii=False, sort_keys=True) if diagnostic else 'null'}"
            )
            if known_block:
                degraded.append(family)
            elif not live_ok:
                failures.append(family)
        except Exception as exc:
            print(f"[FAIL] GET /sec/{family}: {exc!r}")
            failures.append(family)

    bad = session.get(f"{base}/sec/companyfacts?cik=not-a-cik", timeout=args.timeout)
    bad_ok = bad.status_code == 400
    print(f"[{'PASS' if bad_ok else 'FAIL'}] invalid CIK rejected: HTTP {bad.status_code}")
    if not bad_ok:
        failures.append("invalid cik")

    print(json.dumps({"worker": base, "failures": failures, "degraded": degraded}, ensure_ascii=False))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
