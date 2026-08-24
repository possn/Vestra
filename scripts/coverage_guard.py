"""Vestra data-quality guardrails.

Runs after the market pipeline and coverage audit.  It prevents two classes of
silent regressions that previously produced misleading opportunities:

1. malformed European Yahoo symbols (for example ADS-DE.DE), and
2. positive scores/scanner opportunity labels on dossiers with insufficient
   fundamental evidence.

The guard never invents or repairs financial values.  It only validates the
finished stocks.json and exits non-zero when an invariant is violated.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
from collections import Counter

BASE = os.path.dirname(__file__)
STOCKS_PATH = os.path.join(BASE, "..", "data", "stocks.json")
OUT_PATH = os.path.join(BASE, "..", "data", "coverage_guard.json")

EU_SUFFIXES = ("DE", "PA", "AS", "MC", "MI", "SW", "LS", "BR")
# Examples rejected: ADS-DE.DE, ACA-PA.PA, A2A-MI.MI, ABN-AS.AS.
MALFORMED_EU = re.compile(
    r"-(?P<token>" + "|".join(EU_SUFFIXES) + r")\.(?P=token)$",
    re.IGNORECASE,
)


def _n(value):
    try:
        if value is None or value == "":
            return None
        x = float(value)
        return x if x == x and abs(x) != float("inf") else None
    except (TypeError, ValueError):
        return None


def _equity(row):
    return str(row.get("quote_type") or "").upper() not in {
        "ETF", "CRYPTO", "MUTUALFUND", "FUND"
    }


def main() -> int:
    with open(STOCKS_PATH, "r", encoding="utf-8") as fh:
        payload = json.load(fh)
    rows = payload.get("stocks") or []

    violations = []
    counts = Counter()

    for row in rows:
        if not _equity(row):
            continue
        ticker = str(row.get("ticker") or "").upper()
        score = _n(row.get("score"))
        coverage = _n(row.get("data_coverage_pct"))
        critical = _n(row.get("critical_metric_coverage_pct"))
        confidence = _n(row.get("confidence_score"))
        scanner_tags = list(row.get("scanner_tags") or [])
        low52_status = str(row.get("low52_status") or "").lower()
        pipeline_status = str(row.get("pipeline_status") or "")

        if MALFORMED_EU.search(ticker):
            counts["malformed_european_ticker"] += 1
            violations.append({
                "ticker": ticker,
                "type": "malformed_european_ticker",
                "detail": "exchange qualifier duplicated before Yahoo suffix",
            })

        # Metadata-only/carried catalogue rows are allowed to be sparse, but may
        # never be presented as scored opportunities.
        sparse = (coverage is None or coverage < 55) or (critical is not None and critical < 45)
        weak_conf = confidence is None or confidence < 50

        if score is not None and coverage is not None and coverage < 50 and score >= 60:
            counts["high_score_low_coverage"] += 1
            violations.append({
                "ticker": ticker,
                "type": "high_score_low_coverage",
                "score": score,
                "coverage_pct": coverage,
            })

        if score is not None and critical is not None and critical < 35 and score >= 60:
            counts["high_score_low_critical_coverage"] += 1
            violations.append({
                "ticker": ticker,
                "type": "high_score_low_critical_coverage",
                "score": score,
                "critical_coverage_pct": critical,
            })

        if scanner_tags and (sparse or weak_conf):
            counts["scanner_opportunity_without_evidence"] += 1
            violations.append({
                "ticker": ticker,
                "type": "scanner_opportunity_without_evidence",
                "scanner_tags": scanner_tags,
                "coverage_pct": coverage,
                "critical_coverage_pct": critical,
                "confidence_score": confidence,
            })

        if low52_status in {"opportunity", "watch"} and (sparse or weak_conf):
            counts["low52_opportunity_without_evidence"] += 1
            violations.append({
                "ticker": ticker,
                "type": "low52_opportunity_without_evidence",
                "status": low52_status,
                "coverage_pct": coverage,
                "critical_coverage_pct": critical,
                "confidence_score": confidence,
            })

        if pipeline_status in {"equity_catalog_only", "equity_carried_forward"} and scanner_tags:
            counts["catalog_row_ranked"] += 1
            violations.append({
                "ticker": ticker,
                "type": "catalog_row_ranked",
                "pipeline_status": pipeline_status,
            })

    report = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "rows_checked": sum(1 for r in rows if _equity(r)),
        "ok": not violations,
        "violation_count": len(violations),
        "violation_counts": dict(counts),
        "violations": violations[:200],
        "rules": {
            "malformed_european_tickers": "forbidden",
            "score_ge_60_requires_coverage_pct": 50,
            "score_ge_60_requires_critical_coverage_pct": 35,
            "scanner_requires_coverage_pct": 55,
            "scanner_requires_critical_coverage_pct": 45,
            "scanner_requires_confidence_score": 50,
        },
    }
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    if violations:
        print(f"Coverage guard FAILED: {len(violations)} violation(s)")
        for item in violations[:20]:
            print(f" - {item.get('ticker')}: {item.get('type')}")
        return 1
    print(f"Coverage guard OK: {report['rows_checked']} equities checked")
    return 0


if __name__ == "__main__":
    sys.exit(main())
