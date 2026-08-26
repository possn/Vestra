"""Build a lightweight market index plus full dossier shards from data/stocks.json.

Phase 1 migration: stocks.json remains untouched so the current frontend keeps working.
The new files are published in parallel and can be switched on independently later.
"""
from __future__ import annotations

import json
import os
import re
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "data", "stocks.json")
INDEX = os.path.join(ROOT, "data", "stocks-index.json")
SHARD_DIR = os.path.join(ROOT, "data", "dossiers")
MANIFEST = os.path.join(ROOT, "data", "dossiers-manifest.json")

# Keep all scalar fields used by search/scanner/portfolio summaries. Large arrays and
# nested evidence stay in dossier shards and are fetched only when a dossier opens.
SMALL_LIST_KEYS = {
    "data_sources", "opportunity_reasons", "opportunity_cautions",
    "scanner_reasons", "scanner_cautions", "thesis_reasons", "thesis_cautions",
}


def shard_for(ticker: str) -> str:
    c = (ticker or "_").strip().upper()[:1]
    return c if re.match(r"[A-Z0-9]", c) else "_"


def index_row(row: dict) -> dict:
    out = {}
    for k, v in row.items():
        if isinstance(v, (str, int, float, bool)) or v is None:
            out[k] = v
        elif k in SMALL_LIST_KEYS and isinstance(v, list) and len(v) <= 12:
            out[k] = v
    ticker = str(row.get("ticker") or "").upper()
    out["dossier_shard"] = shard_for(ticker)
    # Preserve cheap 52-week range values even when the full history is omitted.
    hist = row.get("price_history_1y") or []
    closes = []
    for item in hist:
        try:
            x = float(item.get("close") if isinstance(item, dict) else item)
            if x > 0:
                closes.append(x)
        except (TypeError, ValueError):
            pass
    if closes:
        out.setdefault("fifty_two_week_low", min(closes))
        out.setdefault("fifty_two_week_high", max(closes))
    return out


def main() -> None:
    with open(SRC, "r", encoding="utf-8") as f:
        payload = json.load(f)
    source_rows = payload.get("stocks") or []
    generated_at = payload.get("generated_at")
    schema_version = payload.get("schema_version")

    # Historical builds can contain the same canonical ticker more than once
    # (for example when a position also belongs to a discovery/index universe).
    # The frontend, manifest and shard dictionaries are ticker-keyed, so enforce
    # the same invariant here: one canonical row per uppercase ticker. The last
    # occurrence wins because late pipeline stages may carry fresher enrichment.
    rows_by_ticker: dict[str, dict] = {}
    duplicate_count = 0
    for row in source_rows:
        ticker = str(row.get("ticker") or "").strip().upper()
        if not ticker:
            continue
        if ticker in rows_by_ticker:
            duplicate_count += 1
        rows_by_ticker[ticker] = row
    rows = list(rows_by_ticker.items())

    shards: dict[str, dict[str, dict]] = defaultdict(dict)
    index_rows = []
    manifest = {}
    for ticker, row in rows:
        key = shard_for(ticker)
        shards[key][ticker] = row
        manifest[ticker] = key
        index_rows.append(index_row(row))

    os.makedirs(SHARD_DIR, exist_ok=True)
    for name in os.listdir(SHARD_DIR):
        if name.endswith(".json"):
            os.remove(os.path.join(SHARD_DIR, name))

    index_payload = {
        "schema_version": schema_version,
        "generated_at": generated_at,
        "data_quality": payload.get("data_quality", {}),
        "universe_counts": payload.get("universe_counts", {}),
        "category_benchmarks": payload.get("category_benchmarks", {}),
        "stocks": index_rows,
    }
    with open(INDEX, "w", encoding="utf-8") as f:
        json.dump(index_payload, f, ensure_ascii=False, separators=(",", ":"))

    for key, values in sorted(shards.items()):
        with open(os.path.join(SHARD_DIR, f"{key}.json"), "w", encoding="utf-8") as f:
            json.dump({"schema_version": schema_version, "generated_at": generated_at, "shard": key, "stocks": values}, f, ensure_ascii=False, separators=(",", ":"))

    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump({
            "schema_version": schema_version,
            "generated_at": generated_at,
            "ticker_count": len(manifest),
            "duplicate_rows_dropped": duplicate_count,
            "tickers": manifest,
        }, f, ensure_ascii=False, separators=(",", ":"))

    src_size = os.path.getsize(SRC)
    idx_size = os.path.getsize(INDEX)
    print(
        f"market shards: {len(index_rows)} unique rows, {len(shards)} shards; "
        f"dropped {duplicate_count} duplicate rows; "
        f"index {idx_size/1_000_000:.2f} MB vs source {src_size/1_000_000:.2f} MB"
    )
    if len(index_rows) != len(manifest):
        raise RuntimeError("Market shard manifest/index cardinality mismatch")
    if src_size > 0 and idx_size >= src_size * 0.60:
        raise RuntimeError("Lightweight index is unexpectedly large (>=60% of stocks.json)")


if __name__ == "__main__":
    main()
