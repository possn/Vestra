"""Vestra data-quality guardrails.

Runs after the market pipeline and coverage audit. It prevents silent regressions
that could make sparse or malformed dossiers look investable.

The guard never invents or repairs financial values. It only validates the
finished stocks.json and exits non-zero when an invariant is violated.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
from collections import Counter

try:
    from coverage_audit import authoritative_quote_type, NON_EQUITY_TYPES
except (ImportError, ModuleNotFoundError):
    from scripts.coverage_audit import authoritative_quote_type, NON_EQUITY_TYPES

BASE = os.path.dirname(__file__)
STOCKS_PATH = os.path.join(BASE, "..", "data", "stocks.json")
OUT_PATH = os.path.join(BASE, "..", "data", "coverage_guard.json")

EU_SUFFIXES = ("DE", "PA", "AS", "MC", "MI", "SW", "LS", "BR")
MALFORMED_EU = re.compile(
    r"-(?P<source>" + "|".join(EU_SUFFIXES) + r")\.(?P<target>"
    + "|".join(EU_SUFFIXES) + r")$",
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
    return authoritative_quote_type(row) not in NON_EQUITY_TYPES


def _add(violations, counts, ticker, kind, **detail):
    counts[kind] += 1
    item = {"ticker": ticker, "type": kind}
    item.update(detail)
    violations.append(item)


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

        opportunity_score = _n(row.get("opportunity_score"))
        opportunity_label = str(row.get("opportunity_label") or "")
        opportunity_eligible = bool(row.get("opportunity_eligible"))
        signal_count = _n(row.get("opportunity_signal_count"))
        structural_count = _n(row.get("opportunity_structural_signal_count"))
        timing_score = _n(row.get("opportunity_timing_score"))
        timing_label = str(row.get("opportunity_timing_label") or "")
        overextended = bool(row.get("opportunity_overextended"))

        malformed_match = MALFORMED_EU.search(ticker)
        if malformed_match:
            _add(
                violations, counts, ticker, "malformed_european_ticker",
                source_exchange_token=malformed_match.group("source").upper(),
                target_yahoo_suffix=malformed_match.group("target").upper(),
                detail="exchange qualifier remained in ticker base before Yahoo suffix",
            )

        if score is not None and (coverage is None or critical is None):
            _add(
                violations, counts, ticker, "score_missing_evidence_metadata",
                score=score, coverage_pct=coverage, critical_coverage_pct=critical,
            )

        sparse = (coverage is None or coverage < 55) or (critical is None or critical < 45)
        weak_conf = confidence is None or confidence < 50

        if score is not None and coverage is not None and coverage < 50 and score >= 60:
            _add(
                violations, counts, ticker, "high_score_low_coverage",
                score=score, coverage_pct=coverage,
            )

        if score is not None and critical is not None and critical < 35 and score >= 60:
            _add(
                violations, counts, ticker, "high_score_low_critical_coverage",
                score=score, critical_coverage_pct=critical,
            )

        if scanner_tags and (sparse or weak_conf):
            _add(
                violations, counts, ticker, "scanner_opportunity_without_evidence",
                scanner_tags=scanner_tags, coverage_pct=coverage,
                critical_coverage_pct=critical, confidence_score=confidence,
            )

        if low52_status in {"opportunity", "watch"} and (sparse or weak_conf):
            _add(
                violations, counts, ticker, "low52_opportunity_without_evidence",
                status=low52_status, coverage_pct=coverage,
                critical_coverage_pct=critical, confidence_score=confidence,
            )

        # Best Opportunities Now is stricter than ordinary scanner tags. It must
        # have strong evidence plus enough independent/structural signals and a
        # usable timing score from current price history.
        if opportunity_score is not None:
            if score is None or sparse or weak_conf:
                _add(
                    violations, counts, ticker, "opportunity_rank_without_evidence",
                    opportunity_score=opportunity_score, score=score,
                    coverage_pct=coverage, critical_coverage_pct=critical,
                    confidence_score=confidence,
                )
            if opportunity_eligible and (
                signal_count is None or signal_count < 5
                or structural_count is None or structural_count < 2
            ):
                _add(
                    violations, counts, ticker, "opportunity_rank_without_structural_depth",
                    opportunity_score=opportunity_score,
                    signal_count=signal_count,
                    structural_signal_count=structural_count,
                )
            if timing_score is None:
                _add(
                    violations, counts, ticker, "opportunity_rank_without_timing",
                    opportunity_score=opportunity_score,
                    timing_label=timing_label,
                )

        # The Discover list is explicitly meant to surface emerging opportunities,
        # not companies whose move is already materially extended. The backend may
        # retain an opportunity score for dossier context, but an overextended name
        # must not qualify as a high-priority actionable opportunity.
        if overextended and opportunity_label in {"Oportunidade forte", "Prioridade alta"}:
            _add(
                violations, counts, ticker, "strong_opportunity_is_overextended",
                label=opportunity_label,
                opportunity_score=opportunity_score,
                timing_score=timing_score,
            )

        if opportunity_label == "Oportunidade forte" and (
            coverage is None or coverage < 65 or confidence is None or confidence < 60
        ):
            _add(
                violations, counts, ticker, "strong_opportunity_below_gate",
                label=opportunity_label, opportunity_score=opportunity_score,
                coverage_pct=coverage, confidence_score=confidence,
            )
        if opportunity_label == "Prioridade alta" and (
            coverage is None or coverage < 75 or confidence is None or confidence < 70
        ):
            _add(
                violations, counts, ticker, "high_priority_opportunity_below_gate",
                label=opportunity_label, opportunity_score=opportunity_score,
                coverage_pct=coverage, confidence_score=confidence,
            )

        if pipeline_status in {"equity_catalog_only", "equity_carried_forward"}:
            if scanner_tags:
                _add(
                    violations, counts, ticker, "catalog_row_ranked",
                    pipeline_status=pipeline_status,
                )
            if opportunity_score is not None or opportunity_eligible:
                _add(
                    violations, counts, ticker, "carried_row_has_active_opportunity_rank",
                    pipeline_status=pipeline_status,
                    opportunity_score=opportunity_score,
                    opportunity_label=opportunity_label,
                )

    report = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "rows_checked": sum(1 for r in rows if _equity(r)),
        "ok": not violations,
        "violation_count": len(violations),
        "violation_counts": dict(counts),
        "violations": violations[:200],
        "rules": {
            "malformed_european_exchange_token_before_suffix": "forbidden",
            "public_score_requires_coverage_and_critical_metadata": True,
            "score_ge_60_requires_coverage_pct": 50,
            "score_ge_60_requires_critical_coverage_pct": 35,
            "scanner_requires_coverage_pct": 55,
            "scanner_requires_critical_coverage_pct": 45,
            "scanner_requires_confidence_score": 50,
            "opportunity_rank_requires_public_score": True,
            "opportunity_rank_requires_signal_count": 5,
            "opportunity_rank_requires_structural_signal_count": 2,
            "opportunity_rank_requires_timing_score": True,
            "strong_opportunities_may_not_be_overextended": True,
            "strong_opportunity_requires_coverage_pct": 65,
            "strong_opportunity_requires_confidence_score": 60,
            "high_priority_requires_coverage_pct": 75,
            "high_priority_requires_confidence_score": 70,
            "carried_rows_may_not_have_active_opportunity_rank": True,
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
