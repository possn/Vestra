#!/usr/bin/env python3
"""Read-only production verification for the Vestra AI Brief boundary.

This verifier never invokes the model. It checks /health and an OPTIONS preflight
for /ai-brief so deployments can be validated without inference cost or output
nondeterminism.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
AI_SOURCE = ROOT / "worker-ai-brief.js"
DEFAULT_ORIGIN = "https://possn.github.io"


def expected_model() -> str:
    text = AI_SOURCE.read_text(encoding="utf-8")
    match = re.search(r"AI_BRIEF_MODEL\s*=\s*'([^']+)'", text)
    if not match:
        raise RuntimeError("AI_BRIEF_MODEL not found in worker-ai-brief.js")
    return match.group(1)


def fail(message: str) -> int:
    print(f"[FAIL] {message}")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--origin", default=DEFAULT_ORIGIN)
    parser.add_argument("--timeout", type=float, default=12.0)
    args = parser.parse_args()

    base = args.url.strip().rstrip("/")
    model = expected_model()
    session = requests.Session()
    session.headers.update({"User-Agent": "Vestra-AI-Brief-Audit/1.0"})

    try:
        health_resp = session.get(
            base + "/health",
            headers={"Accept": "application/json", "Origin": args.origin},
            timeout=args.timeout,
        )
        health = health_resp.json()
    except Exception as exc:
        return fail(f"GET /health failed: {exc!r}")

    if not health_resp.ok or not isinstance(health, dict):
        return fail(f"GET /health HTTP {health_resp.status_code}")
    capabilities = set(health.get("capabilities") or [])
    if "ai_brief" not in capabilities:
        return fail(f"ai_brief missing from capabilities: {sorted(capabilities)!r}")
    if health.get("ai_brief_provider") != "workers_ai":
        return fail(f"unexpected provider: {health.get('ai_brief_provider')!r}")
    if health.get("ai_brief_model") != model:
        return fail(f"model drift: deployed={health.get('ai_brief_model')!r}, source={model!r}")
    if health.get("ai_brief_rate_limit") != "binding":
        return fail(f"rate-limit binding unavailable: {health.get('ai_brief_rate_limit')!r}")
    print(f"[PASS] /health AI brief capability · model={model}")

    try:
        preflight = session.options(
            base + "/ai-brief",
            headers={
                "Origin": args.origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type,x-vestra-session",
            },
            timeout=args.timeout,
        )
    except Exception as exc:
        return fail(f"OPTIONS /ai-brief failed: {exc!r}")

    allow_origin = preflight.headers.get("Access-Control-Allow-Origin", "")
    allow_methods = preflight.headers.get("Access-Control-Allow-Methods", "")
    allow_headers = preflight.headers.get("Access-Control-Allow-Headers", "")
    vary = preflight.headers.get("Vary", "")
    ok = (
        preflight.status_code == 204
        and allow_origin == args.origin
        and "POST" in allow_methods.upper()
        and "content-type" in allow_headers.lower()
        and "x-vestra-session" in allow_headers.lower()
        and "origin" in vary.lower()
    )
    if not ok:
        return fail(json.dumps({
            "status": preflight.status_code,
            "allow_origin": allow_origin,
            "allow_methods": allow_methods,
            "allow_headers": allow_headers,
            "vary": vary,
        }, ensure_ascii=False))
    print("[PASS] OPTIONS /ai-brief · POST + session header + production CORS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
