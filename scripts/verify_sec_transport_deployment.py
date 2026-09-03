#!/usr/bin/env python3
"""Read-only verification of Vestra's deployed SEC transport."""
from __future__ import annotations

import argparse
import json
import sys
from urllib.parse import urlencode

import requests


def clean_base(url: str) -> str:
    return url.strip().rstrip("/")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args()

    base = clean_base(args.url)
    session = requests.Session()
    session.headers.update({"Accept": "application/json", "User-Agent": "Vestra-SEC-Transport-Audit/1.0"})
    failures = []

    try:
        health = session.get(base + "/health", timeout=args.timeout)
        payload = health.json()
        capabilities = payload.get("capabilities") if isinstance(payload, dict) else []
        ok = health.ok and isinstance(capabilities, list) and "sec_transport" in capabilities
        print(f"[{'PASS' if ok else 'FAIL'}] health sec_transport capability: HTTP {health.status_code}")
        if not ok:
            failures.append("health capability")
    except Exception as exc:
        print(f"[FAIL] health sec_transport capability: {exc!r}")
        failures.append("health exception")

    probes = (
        ("companyfacts", 320193, "facts"),
        ("submissions", 320193, "filings"),
    )
    for family, cik, required_key in probes:
        url = f"{base}/sec/{family}?{urlencode({'cik': cik})}"
        try:
            response = session.get(url, timeout=args.timeout)
            payload = response.json()
            valid = response.ok and isinstance(payload, dict) and isinstance(payload.get(required_key), dict)
            source = response.headers.get("X-Vestra-Sec-Source")
            cache = response.headers.get("X-Vestra-Sec-Cache")
            ok = valid and source == "sec.gov" and cache in {"hit", "miss"}
            print(
                f"[{'PASS' if ok else 'FAIL'}] GET /sec/{family}: "
                f"HTTP {response.status_code}, source={source!r}, cache={cache!r}"
            )
            if not ok:
                failures.append(family)
        except Exception as exc:
            print(f"[FAIL] GET /sec/{family}: {exc!r}")
            failures.append(family)

    bad = session.get(f"{base}/sec/companyfacts?cik=not-a-cik", timeout=args.timeout)
    bad_ok = bad.status_code == 400
    print(f"[{'PASS' if bad_ok else 'FAIL'}] invalid CIK rejected: HTTP {bad.status_code}")
    if not bad_ok:
        failures.append("invalid cik")

    print(json.dumps({"worker": base, "failures": failures}, ensure_ascii=False))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
