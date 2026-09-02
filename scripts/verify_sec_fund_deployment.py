#!/usr/bin/env python3
"""Verify the production Worker transports a valid official SEC fund map."""
from __future__ import annotations

import argparse

import requests

SEC_SOURCE = "https://www.sec.gov/files/company_tickers_mf.json"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    args = parser.parse_args()
    base = args.url.rstrip("/")

    response = requests.get(f"{base}/sec-fund-map", timeout=30)
    response.raise_for_status()
    if response.headers.get("X-Vestra-Source") != SEC_SOURCE:
        raise SystemExit(f"unexpected source header: {response.headers.get('X-Vestra-Source')!r}")
    if response.headers.get("X-Vestra-Transport") != "cloudflare-worker":
        raise SystemExit(f"unexpected transport header: {response.headers.get('X-Vestra-Transport')!r}")

    payload = response.json()
    fields = [str(x or "").strip().lower() for x in (payload.get("fields") or [])]
    rows = payload.get("data") or []
    if "cik" not in fields or "symbol" not in fields or len(rows) < 1000:
        raise SystemExit(f"invalid SEC fund payload: fields={fields!r}, rows={len(rows)}")

    print(f"SEC fund Worker transport OK: {len(rows)} official SEC rows")


if __name__ == "__main__":
    main()
