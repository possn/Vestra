"""Synchronise Worker-discovered instruments into the canonical Vestra universe.

The browser may discover a valid company before it exists in the daily
pre-enriched catalogue. The Cloudflare Worker stores those validated symbols in
its learned-universe Durable Object. This script runs before the heavy market
pipeline, snapshots the central catalogue to data/learned_tickers.json, and
merges the symbols into data/extra_tickers.json so the existing universe builder
and scoring pipeline pick them up without a parallel ingestion path.

Schema v2 treats a reachable Worker catalogue as authoritative. The previous
snapshot remains a fallback only when the Worker is unavailable. During the v1
identity migration, a legacy learned ticker is retired from extra_tickers only
when the previous hygiene audit also classified that exact ticker as unresolved.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
EXTRA_PATH = ROOT / "data" / "extra_tickers.json"
SNAPSHOT_PATH = ROOT / "data" / "learned_tickers.json"
HYGIENE_PATH = ROOT / "data" / "extra_ticker_hygiene.json"
WORKER_URL = os.getenv(
    "VESTRA_WORKER_URL",
    "https://delicate-bar-cc80.pedrossnunes.workers.dev",
).rstrip("/")
TICKER_RE = re.compile(r"^[A-Z0-9][A-Z0-9.\-]{0,14}$")
ALLOWED_TYPES = {"EQUITY", "ETF", "MUTUALFUND"}


def _load_json(path: Path, default):
    try:
        with path.open(encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return default


def _valid_rows(payload):
    rows = payload.get("rows", []) if isinstance(payload, dict) else []
    out = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        ticker = str(row.get("ticker") or "").strip().upper()
        quote_type = str(row.get("quote_type") or "EQUITY").strip().upper()
        if not TICKER_RE.fullmatch(ticker) or quote_type not in ALLOWED_TYPES:
            continue
        out.append({
            "ticker": ticker,
            "name": str(row.get("name") or ticker).strip(),
            "exchange": str(row.get("exchange") or "").strip(),
            "currency": str(row.get("currency") or "").strip().upper(),
            "quote_type": quote_type,
            "sector": str(row.get("sector") or "").strip(),
            "industry": str(row.get("industry") or "").strip(),
            "country": str(row.get("country") or "").strip(),
            "first_seen": str(row.get("first_seen") or "").strip(),
            "last_seen": str(row.get("last_seen") or "").strip(),
            "validation_count": int(row.get("validation_count") or 1),
        })
    dedup = {row["ticker"]: row for row in out}
    return sorted(dedup.values(), key=lambda x: x["ticker"])


def fetch_remote_rows():
    request = Request(
        f"{WORKER_URL}/learned-universe",
        headers={"Accept": "application/json", "User-Agent": "VestraPipeline/2.0"},
    )
    with urlopen(request, timeout=15) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return _valid_rows(payload)


def _unresolved_tickers(payload):
    if not isinstance(payload, dict):
        return set()
    return {
        str(value or "").strip().upper()
        for value in payload.get("unresolved_tickers", [])
        if str(value or "").strip()
    }


def merge_extra_tickers(rows, previous_rows=(), hygiene_payload=None):
    payload = _load_json(EXTRA_PATH, {})
    if not isinstance(payload, dict):
        payload = {"tickers": payload if isinstance(payload, list) else []}
    existing = {
        str(x).strip().upper()
        for x in payload.get("tickers", [])
        if str(x).strip()
    }
    learned = {row["ticker"] for row in rows}
    previous_learned = {row["ticker"] for row in previous_rows}
    unresolved = _unresolved_tickers(hygiene_payload or {})
    retired = previous_learned & unresolved
    merged = sorted((existing - retired) | learned)
    payload["tickers"] = merged
    payload["learned_from_search"] = len(learned)
    payload["learned_snapshot"] = "data/learned_tickers.json"
    payload["learned_identity_schema"] = 2
    payload["retired_unverified_learned"] = sorted(retired)
    EXTRA_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return len(existing), len(merged), sorted(retired)


def main():
    previous = _valid_rows(_load_json(SNAPSHOT_PATH, {}))
    hygiene = _load_json(HYGIENE_PATH, {})
    try:
        rows = fetch_remote_rows()
        source = "worker-authoritative-v2"
    except Exception as exc:
        rows = previous
        source = "snapshot-fallback"
        print(f"Learned universe remote unavailable; using snapshot: {exc}")

    snapshot = {
        "schema_version": 2,
        "source": source,
        "worker_url": WORKER_URL,
        "count": len(rows),
        "rows": rows,
    }
    SNAPSHOT_PATH.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    before, after, retired = merge_extra_tickers(rows, previous, hygiene)
    suffix = f"; retired legacy unresolved: {', '.join(retired)}" if retired else ""
    print(f"Learned universe: {len(rows)} validated ticker(s); extra universe {before} -> {after}{suffix}")


if __name__ == "__main__":
    main()
