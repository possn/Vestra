"""Build a compact coverage audit from data/stocks.json.

The audit is diagnostic only: it never changes scores. It quantifies where
fundamental retrieval is still weak after Yahoo + SEC + ESEF + targeted gap
recovery so source work can be directed at the real holes.
"""
from __future__ import annotations

import collections
import datetime as dt
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "stocks.json"
OUT = ROOT / "data" / "coverage_audit.json"


def f(v):
    try:
        x = float(v)
        return x if x == x and abs(x) != float("inf") else None
    except (TypeError, ValueError):
        return None


def equity_rows(payload):
    return [
        r for r in (payload.get("stocks") or [])
        if r.get("quote_type") not in ("ETF", "CRYPTO")
    ]


def bucket(cov):
    if cov is None:
        return "unknown"
    if cov < 50:
        return "lt50"
    if cov < 65:
        return "50_64"
    if cov < 80:
        return "65_79"
    return "gte80"


def row_sources(r):
    src = r.get("data_sources") or []
    if isinstance(src, str):
        src = [src]
    return sorted({str(x) for x in src if x})


def summarize_group(rows):
    covs = [f(r.get("data_coverage_pct")) for r in rows]
    covs = [x for x in covs if x is not None]
    counts = collections.Counter(bucket(f(r.get("data_coverage_pct"))) for r in rows)
    return {
        "count": len(rows),
        "avg_coverage_pct": round(sum(covs) / len(covs), 1) if covs else None,
        "lt50": counts.get("lt50", 0),
        "50_64": counts.get("50_64", 0),
        "65_79": counts.get("65_79", 0),
        "gte80": counts.get("gte80", 0),
    }


def main():
    payload = json.loads(SRC.read_text(encoding="utf-8"))
    rows = equity_rows(payload)

    by_region = collections.defaultdict(list)
    by_model = collections.defaultdict(list)
    source_hits = collections.Counter()
    missing_metric = collections.Counter()

    critical = [
        "roe", "roa", "profit_margin", "operating_margin", "gross_margin",
        "revenue_growth", "earnings_growth", "free_cash_flow",
        "operating_cash_flow", "current_ratio", "quick_ratio",
        "debt_to_equity", "trailing_pe", "forward_pe", "price_to_book",
        "enterprise_to_ebitda", "roce_proxy",
    ]

    for r in rows:
        by_region[str(r.get("region") or "Unknown")].append(r)
        by_model[str(r.get("score_model") or "general")].append(r)
        for s in row_sources(r):
            source_hits[s] += 1
        for key in critical:
            if r.get(key) is None:
                missing_metric[key] += 1

    sparse = sorted(
        rows,
        key=lambda r: (f(r.get("data_coverage_pct")) if f(r.get("data_coverage_pct")) is not None else -1),
    )[:100]

    audit = {
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "equities": summarize_group(rows),
        "by_region": {k: summarize_group(v) for k, v in sorted(by_region.items())},
        "by_score_model": {k: summarize_group(v) for k, v in sorted(by_model.items())},
        "source_coverage": dict(source_hits.most_common()),
        "most_missing_critical_metrics": [
            {"metric": k, "missing": n, "missing_pct": round(n / len(rows) * 100, 1) if rows else 0}
            for k, n in missing_metric.most_common()
        ],
        "sparsest_dossiers": [
            {
                "ticker": r.get("ticker"),
                "name": r.get("name"),
                "region": r.get("region"),
                "score_model": r.get("score_model"),
                "coverage_pct": f(r.get("data_coverage_pct")),
                "critical_coverage_pct": f(r.get("critical_metric_coverage_pct")),
                "score_reliability": r.get("score_reliability"),
                "sources": row_sources(r),
                "gap_retrieval_attempted": bool(r.get("gap_retrieval_attempted")),
                "gap_retrieval_filled": r.get("gap_retrieval_filled"),
            }
            for r in sparse
        ],
    }
    OUT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Coverage audit: {len(rows)} equities -> {OUT}")


if __name__ == "__main__":
    main()
