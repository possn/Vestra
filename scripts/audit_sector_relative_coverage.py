#!/usr/bin/env python3
"""Read-only coverage audit of observed sector-relative evidence in canonical stocks."""
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

FIELDS = (
    "opportunity_stock_return_20d_pct",
    "opportunity_sector_return_20d_pct",
    "opportunity_sector_benchmark_ticker",
    "opportunity_sector_benchmark_asof_date",
    "opportunity_sector_benchmark_verified",
)

def report(payload):
    rows = payload.get("stocks", []) if isinstance(payload, dict) else []
    if not isinstance(rows, list):
        raise ValueError("stocks must be an array")
    by_sector = defaultdict(Counter)
    total = Counter()
    for row in rows:
        if not isinstance(row, dict) or str(row.get("quote_type", "")).upper() in {"ETF", "CRYPTO"}:
            continue
        sector = str(row.get("sector") or "unknown")
        ticker = str(row.get("ticker") or "")
        # ETF peers are intended for US-style unsuffixed equity tickers only.
        if not ticker or "." in ticker:
            continue
        b = by_sector[sector]
        b["eligible"] += 1
        total["eligible"] += 1
        fields_present = [row.get(k) is not None for k in FIELDS]
        verified = row.get("opportunity_sector_benchmark_verified") is True
        if verified and all(fields_present):
            b["verified"] += 1
            total["verified"] += 1
        elif any(fields_present):
            b["incomplete"] += 1
            total["incomplete"] += 1
        else:
            b["unavailable"] += 1
            total["unavailable"] += 1
    def encode(c):
        n = c["eligible"]
        return {k: c[k] for k in ("eligible", "verified", "incomplete", "unavailable")} | {
            "coverage_pct": round(100 * c["verified"] / n, 2) if n else None
        }
    return {
        "source_generated_at": payload.get("generated_at") if isinstance(payload, dict) else None,
        "interpretation": "Observed published fields only; not a performance or alpha test",
        "total": encode(total),
        "sectors": {k: encode(v) for k, v in sorted(by_sector.items())},
    }

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stocks_json", type=Path, help="Canonical generated stocks JSON")
    parser.add_argument("--min-coverage", type=float, default=None,
                        help="Optional minimum total verified coverage %% (exit 2 if below)")
    args = parser.parse_args()
    payload = json.loads(args.stocks_json.read_text(encoding="utf-8"))
    result = report(payload)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if args.min_coverage is not None:
        pct = result["total"]["coverage_pct"]
        if pct is None or pct < args.min_coverage:
            raise SystemExit(2)

if __name__ == "__main__":
    main()
