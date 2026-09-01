"""Build an actionable coverage audit from data/stocks.json.

The audit is diagnostic only: it never changes scores. It quantifies where
fundamental retrieval is still weak after Yahoo + SEC + ESEF + targeted gap
recovery so source work can be directed at the real holes.
"""
from __future__ import annotations

import collections
import datetime as dt
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "stocks.json"
OUT = ROOT / "data" / "coverage_audit.json"

EU_SUFFIXES = ("DE", "PA", "AS", "MC", "MI", "SW", "LS", "BR")
MALFORMED_EU = re.compile(
    r"-(?P<source>" + "|".join(EU_SUFFIXES) + r")\.(?P<target>"
    + "|".join(EU_SUFFIXES) + r")$",
    re.IGNORECASE,
)

CRITICAL_METRICS = (
    "roe", "roa", "profit_margin", "operating_margin", "gross_margin",
    "revenue_growth", "earnings_growth", "free_cash_flow",
    "operating_cash_flow", "current_ratio", "quick_ratio",
    "debt_to_equity", "trailing_pe", "forward_pe", "price_to_book",
    "enterprise_to_ebitda", "roce_proxy",
)

NON_EQUITY_TYPES = {"ETF", "CRYPTO", "MUTUALFUND", "FUND"}
US_REGIONS = {"United States", "USA", "US"}
EU_REGIONS = {
    "Austria", "Belgium", "Denmark", "Finland", "France", "Germany",
    "Ireland", "Italy", "Luxembourg", "Netherlands", "Norway", "Portugal",
    "Spain", "Sweden", "Switzerland",
}


def f(v):
    try:
        if v is None or v == "":
            return None
        x = float(v)
        return x if x == x and abs(x) != float("inf") else None
    except (TypeError, ValueError):
        return None


def normalized_quote_type(row):
    return str(row.get("quote_type") or "").strip().upper()


def equity_rows(payload):
    return [
        r for r in (payload.get("stocks") or [])
        if normalized_quote_type(r) not in NON_EQUITY_TYPES
    ]


def identity_state(row):
    quote_type = normalized_quote_type(row)
    if quote_type in NON_EQUITY_TYPES:
        return "non_equity"
    if not quote_type:
        return "unresolved"
    return "confirmed_equity"


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


def missing_critical_metrics(row):
    return [key for key in CRITICAL_METRICS if row.get(key) is None]


def retrieval_lane(row, missing=None):
    """Return the next deterministic retrieval lane for a sparse dossier.

    Identity must be known before the audit recommends a fundamental source.
    This prevents a throttled/missing quote type from silently being treated as
    a confirmed equity and routed to SEC/ESEF or statement retrieval.
    """
    missing = list(missing if missing is not None else missing_critical_metrics(row))
    if not missing:
        return "none"
    if identity_state(row) == "unresolved":
        return "identity_unresolved"

    sources = set(row_sources(row))
    region = str(row.get("region") or "Unknown")
    ticker = str(row.get("ticker") or "").upper()

    if region in US_REGIONS and "SEC EDGAR" not in sources:
        return "sec_edgar"
    if region in EU_REGIONS and "ESEF / filings.xbrl.org" not in sources:
        return "esef"
    if not bool(row.get("gap_statement_enriched")):
        return "annual_statement_gap"
    if not bool(row.get("quarterly_gap_enriched")):
        return "quarterly_ttm_gap"
    if "forward_pe" in missing and "Analyst feed" not in sources:
        return "analyst_estimates"
    if ticker.endswith(".L") and not row.get("isin"):
        return "lse_identity"
    return "unresolved"


def actionable_gap(row):
    missing = missing_critical_metrics(row)
    coverage = f(row.get("data_coverage_pct"))
    critical_coverage = f(row.get("critical_metric_coverage_pct"))
    return {
        "ticker": row.get("ticker"),
        "name": row.get("name"),
        "region": row.get("region"),
        "quote_type": normalized_quote_type(row) or None,
        "identity_state": identity_state(row),
        "score_model": row.get("score_model") or "general",
        "coverage_pct": coverage,
        "critical_coverage_pct": critical_coverage,
        "missing_critical_count": len(missing),
        "missing_critical_metrics": missing,
        "recommended_retrieval_lane": retrieval_lane(row, missing),
        "score_reliability": row.get("score_reliability"),
        "evidence_state": (row.get("data_provenance") or {}).get("evidence_state"),
        "sources": row_sources(row),
    }


def gap_priority(item):
    critical = item.get("critical_coverage_pct")
    coverage = item.get("coverage_pct")
    return (
        critical if critical is not None else -1,
        coverage if coverage is not None else -1,
        -int(item.get("missing_critical_count") or 0),
        str(item.get("ticker") or ""),
    )


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
    all_rows = [r for r in (payload.get("stocks") or []) if isinstance(r, dict)]
    rows = equity_rows(payload)

    by_region = collections.defaultdict(list)
    by_model = collections.defaultdict(list)
    source_hits = collections.Counter()
    missing_metric = collections.Counter()
    reliability = collections.Counter()
    opportunity_labels = collections.Counter()
    opportunity_suppressed = collections.Counter()
    retrieval_lanes = collections.Counter()
    retrieval_by_region = collections.defaultdict(collections.Counter)
    retrieval_by_model = collections.defaultdict(collections.Counter)
    identity_states = collections.Counter(identity_state(r) for r in all_rows)
    unresolved_identity = [r for r in rows if identity_state(r) == "unresolved"]
    malformed = []
    annual_attempted = 0
    annual_enriched = 0
    annual_gain = []
    quarterly_attempted = 0
    quarterly_enriched = 0
    quarterly_gain = []
    actionable = []

    for r in rows:
        region = str(r.get("region") or "Unknown")
        model = str(r.get("score_model") or "general")
        by_region[region].append(r)
        by_model[model].append(r)
        for s in row_sources(r):
            source_hits[s] += 1
        for key in CRITICAL_METRICS:
            if r.get(key) is None:
                missing_metric[key] += 1

        reliability[str(r.get("score_reliability") or "unknown")] += 1
        opportunity_labels[str(r.get("opportunity_label") or "none")] += 1
        reason = str(r.get("opportunity_suppressed_reason") or "").strip()
        if reason:
            opportunity_suppressed[reason] += 1

        ticker = str(r.get("ticker") or "").upper()
        if MALFORMED_EU.search(ticker):
            malformed.append(ticker)

        before = f(r.get("gap_coverage_before"))
        after = f(r.get("gap_coverage_after"))
        enriched = bool(r.get("gap_statement_enriched"))
        if before is not None or after is not None or enriched:
            annual_attempted += 1
        if enriched:
            annual_enriched += 1
        if before is not None and after is not None:
            annual_gain.append(after - before)

        q_before = f(r.get("quarterly_gap_coverage_before"))
        q_after = f(r.get("quarterly_gap_coverage_after"))
        q_enriched = bool(r.get("quarterly_gap_enriched"))
        if q_before is not None or q_after is not None or q_enriched:
            quarterly_attempted += 1
        if q_enriched:
            quarterly_enriched += 1
        if q_before is not None and q_after is not None:
            quarterly_gain.append(q_after - q_before)

        item = actionable_gap(r)
        if item["missing_critical_count"]:
            actionable.append(item)
            lane = item["recommended_retrieval_lane"]
            retrieval_lanes[lane] += 1
            retrieval_by_region[region][lane] += 1
            retrieval_by_model[model][lane] += 1

    sparse = sorted(
        rows,
        key=lambda r: (f(r.get("data_coverage_pct")) if f(r.get("data_coverage_pct")) is not None else -1),
    )[:100]
    actionable.sort(key=gap_priority)

    audit = {
        "schema_version": 3,
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "equities": summarize_group(rows),
        "asset_type_hygiene": {
            "states": dict(identity_states.most_common()),
            "unresolved_equity_candidate_count": len(unresolved_identity),
            "unresolved_equity_candidate_examples": [
                {
                    "ticker": r.get("ticker"),
                    "name": r.get("name"),
                    "region": r.get("region"),
                    "coverage_pct": f(r.get("data_coverage_pct")),
                    "sources": row_sources(r),
                }
                for r in unresolved_identity[:100]
            ],
        },
        "by_region": {k: summarize_group(v) for k, v in sorted(by_region.items())},
        "by_score_model": {k: summarize_group(v) for k, v in sorted(by_model.items())},
        "source_coverage": dict(source_hits.most_common()),
        "score_reliability": dict(reliability.most_common()),
        "opportunity_labels": dict(opportunity_labels.most_common()),
        "opportunity_suppressed_reasons": dict(opportunity_suppressed.most_common()),
        "ticker_hygiene": {
            "malformed_european_count": len(malformed),
            "malformed_european_examples": malformed[:50],
        },
        "gap_retrieval": {
            "annual": {
                "rows_with_metadata": annual_attempted,
                "rows_enriched": annual_enriched,
                "avg_critical_coverage_gain_pp": round(sum(annual_gain) / len(annual_gain), 1) if annual_gain else None,
            },
            "quarterly_ttm": {
                "rows_with_metadata": quarterly_attempted,
                "rows_enriched": quarterly_enriched,
                "avg_critical_coverage_gain_pp": round(sum(quarterly_gain) / len(quarterly_gain), 1) if quarterly_gain else None,
            },
        },
        "most_missing_critical_metrics": [
            {"metric": k, "missing": n, "missing_pct": round(n / len(rows) * 100, 1) if rows else 0}
            for k, n in missing_metric.most_common()
        ],
        "retrieval_priority": {
            "rows_with_critical_gaps": len(actionable),
            "recommended_lane_impact": dict(retrieval_lanes.most_common()),
            "by_region": {
                region: dict(counter.most_common())
                for region, counter in sorted(retrieval_by_region.items())
            },
            "by_score_model": {
                model: dict(counter.most_common())
                for model, counter in sorted(retrieval_by_model.items())
            },
            "top_actionable_dossiers": actionable[:200],
        },
        "sparsest_dossiers": [
            {
                "ticker": r.get("ticker"),
                "name": r.get("name"),
                "region": r.get("region"),
                "quote_type": normalized_quote_type(r) or None,
                "identity_state": identity_state(r),
                "score_model": r.get("score_model"),
                "coverage_pct": f(r.get("data_coverage_pct")),
                "critical_coverage_pct": f(r.get("critical_metric_coverage_pct")),
                "missing_critical_metrics": missing_critical_metrics(r),
                "recommended_retrieval_lane": retrieval_lane(r),
                "score_raw": f(r.get("score_raw")),
                "score": f(r.get("score")),
                "score_reliability": r.get("score_reliability"),
                "sources": row_sources(r),
                "gap_statement_enriched": bool(r.get("gap_statement_enriched")),
                "gap_coverage_before": f(r.get("gap_coverage_before")),
                "gap_coverage_after": f(r.get("gap_coverage_after")),
                "quarterly_gap_enriched": bool(r.get("quarterly_gap_enriched")),
                "quarterly_gap_coverage_before": f(r.get("quarterly_gap_coverage_before")),
                "quarterly_gap_coverage_after": f(r.get("quarterly_gap_coverage_after")),
                "opportunity_eligible": r.get("opportunity_eligible"),
                "opportunity_score": f(r.get("opportunity_score")),
                "opportunity_suppressed_reason": r.get("opportunity_suppressed_reason"),
            }
            for r in sparse
        ],
    }
    OUT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Coverage audit: {len(rows)} equities -> {OUT}")


if __name__ == "__main__":
    main()
