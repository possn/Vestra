"""Read-only overlap audit for published Vestra strategy signals.

The general best_opportunities lens is a baseline, not independent evidence.
No scores, eligibility rules, or scanner files are modified by this script.
"""
import argparse
import json
from collections import Counter
from itertools import combinations
from pathlib import Path

GENERAL = "best_opportunities"


def audit(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get("tickers"), dict):
        raise ValueError("Expected scanner JSON with tickers object")
    rows = payload["tickers"]
    counts = Counter()
    pairs = Counter()
    distribution = Counter()
    specialized = 0
    general_only = 0
    missing_general = 0
    invalid_rows = 0
    for ticker, signals in rows.items():
        if not isinstance(ticker, str) or not ticker.strip() or not isinstance(signals, dict):
            invalid_rows += 1
            continue
        lenses = sorted(k for k, value in signals.items()
                        if isinstance(k, str) and isinstance(value, dict))
        if not lenses:
            invalid_rows += 1
            continue
        counts.update(lenses)
        distribution[len(lenses)] += 1
        pairs.update(tuple(pair) for pair in combinations(lenses, 2))
        specialized += int(any(k != GENERAL for k in lenses))
        general_only += int(lenses == [GENERAL])
        missing_general += int(GENERAL not in lenses)
    valid = sum(distribution.values())
    return {
        "schema": "vestra_scanner_overlap_audit_v1",
        "source_generated_at": payload.get("generated_at"),
        "declared_ticker_count": payload.get("ticker_count"),
        "unique_valid_tickers": valid,
        "invalid_or_empty_ticker_rows": invalid_rows,
        "strategies": dict(sorted(counts.items())),
        "lens_count_distribution": {str(k): v for k, v in sorted(distribution.items())},
        "multi_lens_tickers": sum(v for k, v in distribution.items() if k > 1),
        "specialized_tickers": specialized,
        "general_only_tickers": general_only,
        "specialized_without_general": missing_general,
        "pair_overlaps": [
            {"strategy_a": a, "strategy_b": b, "ticker_count": count}
            for (a, b), count in sorted(pairs.items(), key=lambda kv: (-kv[1], kv[0]))
        ],
        "interpretation": "Co-occurring labels are not proof of duplicate scoring, independent evidence, or predictive edge.",
        "read_only": True,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/stocks-scanner.json")
    args = parser.parse_args()
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    print(json.dumps(audit(payload), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
