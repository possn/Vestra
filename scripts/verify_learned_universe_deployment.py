#!/usr/bin/env python3
"""Read-only production contract check for Vestra's learned-universe router."""
from __future__ import annotations

import argparse
import json
import sys
from urllib.request import Request, urlopen

EXPECTED_ORIGIN = "https://possn.github.io"


def get_json(url: str, origin: str, timeout: float):
    req = Request(url, headers={"Accept": "application/json", "Origin": origin, "User-Agent": "Vestra-Learned-Universe-Audit/1.0"})
    with urlopen(req, timeout=timeout) as response:
        return response.status, dict(response.headers), json.loads(response.read().decode("utf-8"))


def preflight(url: str, origin: str, timeout: float):
    req = Request(
        url,
        method="OPTIONS",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
            "User-Agent": "Vestra-Learned-Universe-Audit/1.0",
        },
    )
    with urlopen(req, timeout=timeout) as response:
        return response.status, dict(response.headers)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--origin", default=EXPECTED_ORIGIN)
    parser.add_argument("--timeout", type=float, default=12.0)
    args = parser.parse_args()
    base = args.url.rstrip("/")
    failures = []

    try:
        status, _, health = get_json(base + "/health", args.origin, args.timeout)
        capabilities = health.get("capabilities", []) if isinstance(health, dict) else []
        if status != 200 or "learned_universe" not in capabilities:
            failures.append(f"health capability missing: status={status}, capabilities={capabilities!r}")
        if not isinstance(health, dict) or health.get("learned_universe_storage") != "durable_object":
            failures.append(f"storage contract missing: {health.get('learned_universe_storage') if isinstance(health, dict) else None!r}")
    except Exception as exc:
        failures.append(f"health request failed: {exc!r}")

    try:
        status, headers, payload = get_json(base + "/learned-universe", args.origin, args.timeout)
        rows = payload.get("rows") if isinstance(payload, dict) else None
        count = payload.get("count") if isinstance(payload, dict) else None
        if status != 200:
            failures.append(f"GET /learned-universe HTTP {status}")
        if not isinstance(payload, dict) or payload.get("schema_version") != 1 or not isinstance(rows, list) or not isinstance(count, int):
            failures.append(f"invalid learned-universe payload: {payload!r}")
        allow = headers.get("Access-Control-Allow-Origin", "")
        if allow != args.origin:
            failures.append(f"learned-universe CORS mismatch: {allow!r}")
        print(json.dumps({"status": status, "count": count, "rows_sample": (rows or [])[:3]}, ensure_ascii=False))
    except Exception as exc:
        failures.append(f"learned-universe request failed: {exc!r}")

    # Read-only POST-path verification: exercise the browser's CORS preflight
    # without creating or mutating a learned ticker in production.
    try:
        status, headers = preflight(base + "/learned-universe", args.origin, args.timeout)
        allow_origin = headers.get("Access-Control-Allow-Origin", "")
        allow_methods = {
            part.strip().upper()
            for part in headers.get("Access-Control-Allow-Methods", "").split(",")
            if part.strip()
        }
        allow_headers = {
            part.strip().lower()
            for part in headers.get("Access-Control-Allow-Headers", "").split(",")
            if part.strip()
        }
        if status not in (200, 204):
            failures.append(f"OPTIONS /learned-universe HTTP {status}")
        if allow_origin != args.origin:
            failures.append(f"learned-universe preflight origin mismatch: {allow_origin!r}")
        if "POST" not in allow_methods or "OPTIONS" not in allow_methods:
            failures.append(f"learned-universe preflight methods missing POST/OPTIONS: {sorted(allow_methods)!r}")
        if "content-type" not in allow_headers:
            failures.append(f"learned-universe preflight headers missing content-type: {sorted(allow_headers)!r}")
    except Exception as exc:
        failures.append(f"learned-universe preflight failed: {exc!r}")

    if failures:
        for failure in failures:
            print(f"[FAIL] {failure}")
        return 1
    print("[PASS] learned-universe router + Durable Object + POST preflight contract")
    return 0


if __name__ == "__main__":
    sys.exit(main())
