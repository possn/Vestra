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

from known_asset_identity import exact_identity_override
from ticker_successors import successor_for

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
_CATALOG_ETF_TICKERS = None


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


def catalog_etf_tickers():
    """Load the deterministic ETF catalogue only when identity needs it.

    Production executes this file from ``scripts/`` so the universe module is
    directly importable. Lightweight unit tests intentionally do not install
    yfinance/pandas; in that context absence of the catalogue simply disables
    the fallback rather than making the audit module unimportable. Tests that
    exercise the fallback inject a dependency-free universe stub explicitly.
    """
    global _CATALOG_ETF_TICKERS
    if _CATALOG_ETF_TICKERS is None:
        try:
            from universe import ETF_UNIVERSE
        except (ImportError, ModuleNotFoundError):
            ETF_UNIVERSE = {}
        _CATALOG_ETF_TICKERS = frozenset(
            str(ticker or "").strip().upper()
            for ticker in ETF_UNIVERSE
            if str(ticker or "").strip()
        )
    return _CATALOG_ETF_TICKERS


def authoritative_identity_evidence(row):
    """Return the exact deterministic identity source used by runtime/audit."""
    ticker = str(row.get("ticker") or "").strip().upper()
    override = exact_identity_override(ticker)
    if isinstance(override, dict) and str(override.get("quote_type") or "").strip():
        return "known_asset_identity"
    successor = successor_for(ticker)
    if isinstance(successor, dict) and str(successor.get("quote_type") or "").strip():
        return "ticker_successor"
    if ticker in catalog_etf_tickers():
        return "etf_catalog"
    return ""


def authoritative_quote_type(row):
    """Return a fail-closed type using only explicit deterministic evidence.

    A live reported type always wins. If the provider lost the type entirely,
    audit routing may recover it from the same exact-match identity contracts
    used by runtime (known broker identities, official ticker successors, ETF
    catalogue). Nothing is ever guessed to be an equity from absence of data.
    """
    quote_type = normalized_quote_type(row)
    if quote_type:
        return quote_type
    ticker = str(row.get("ticker") or "").strip().upper()
    override = exact_identity_override(ticker)
    if isinstance(override, dict):
        override_type = str(override.get("quote_type") or "").strip().upper()
        if override_type:
            return override_type
    successor = successor_for(ticker)
    if isinstance(successor, dict):
        successor_type = str(successor.get("quote_type") or "").strip().upper()
        if successor_type:
            return successor_type
    if ticker in catalog_etf_tickers():
        return "ETF"
    return ""


def equity_rows(payload):
    return [
        r for r in (payload.get("stocks") or [])
        if authoritative_quote_type(r) not in NON_EQUITY_TYPES
    ]


def identity_state(row):
    quote_type = authoritative_quote_type(row)
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
        "quote_type": authoritative_quote_type(row) or None,
        "reported_quote_type": normalized_quote_type(row) or None,
        "identity_state": identity_state(row),
        "identity_evidence": authoritative_identity_evidence(row) or None,
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
    recovered_identity = [
        r for r in all_rows
        if not normalized_quote_type(r) and authoritative_quote_type(r)
    ]
    recovered_by_evidence = collections.Counter(
        authoritative_identity_evidence(r) or "unknown" for r in recovered_identity
    )
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
        "schema_version": 5,
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "equities": summarize_group(rows),
        "asset_type_hygiene": {
            "states": dict(identity_states.most_common()),
            "authoritative_identity_recoveries": len(recovered_identity),
            "authoritative_identity_recoveries_by_evidence": dict(recovered_by_evidence.most_common()),
            "authoritative_identity_examples": [
                {
                    "ticker": r.get("ticker"),
                    "region": r.get("region"),
                    "quote_type": authoritative_quote_type(r),
                    "identity_evidence": authoritative_identity_evidence(r) or None,
                }
                for r in recovered_identity[:100]
            ],
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
                "quote_type": authoritative_quote_type(r) or None,
                "reported_quote_type": normalized_quote_type(r) or None,
                "identity_state": identity_state(r),
                "identity_evidence": authoritative_identity_evidence(r) or None,
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
