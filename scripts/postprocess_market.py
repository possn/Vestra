"""Final market-row hygiene and late-stage opportunity refresh.

Runs after run.py has completed all universe-level overlays (including recovery
confirmation). This solves two ordering/freshness problems without inventing any
fundamental data:

1. Best Opportunities is recalculated after recovery_score exists for the
   current run, so the ranking can use same-run recovery evidence.
2. Metadata-only / carried-forward equities cannot retain stale scanner,
   low-52-opportunity or Best Opportunities fields from an older dataset.

The module only rewrites derived ranking fields in data/stocks.json.
"""
from __future__ import annotations

import json
import os

from opportunity_rank import assess as assess_opportunity

BASE = os.path.dirname(__file__)
STOCKS_PATH = os.path.join(BASE, "..", "data", "stocks.json")

STALE_DERIVED_KEYS = {
    "opportunity_score",
    "opportunity_score_raw",
    "opportunity_label",
    "opportunity_reasons",
    "opportunity_cautions",
    "opportunity_components",
    "opportunity_eligible",
    "opportunity_suppressed_reason",
    "opportunity_signal_count",
    "opportunity_structural_signal_count",
    "opportunity_gates",
    "opportunity_caps",
    "scanner_tags",
    "scanner_results",
    "scanner_best",
    "scanner_best_score",
    "low52_opportunity_score",
}


def _n(v):
    try:
        if v is None or v == "":
            return None
        x = float(v)
        return x if x == x and abs(x) != float("inf") else None
    except (TypeError, ValueError):
        return None


def _is_fund(row: dict) -> bool:
    return str(row.get("quote_type") or "").upper() in {
        "ETF", "CRYPTO", "MUTUALFUND", "FUND"
    }


def _refresh_best_scanner(row: dict) -> None:
    results = row.get("scanner_results")
    if not isinstance(results, dict):
        results = {}

    opp = _n(row.get("opportunity_score"))
    eligible = row.get("opportunity_eligible") is True and opp is not None

    if eligible:
        results["best_opportunities"] = {
            "score": opp,
            "label": str(row.get("opportunity_label") or "Best Opportunities"),
            "reason": "Ranking estrutural evidence-gated",
        }
    else:
        results.pop("best_opportunities", None)

    row["scanner_results"] = results

    tags = [str(x) for x in (row.get("scanner_tags") or []) if x]
    tags = [x for x in tags if x != "best_opportunities"]
    if eligible:
        tags.insert(0, "best_opportunities")
    row["scanner_tags"] = tags

    if eligible:
        row["scanner_best"] = "best_opportunities"
        row["scanner_best_score"] = opp
        return

    # If a previous run had Best Opportunities as the preferred strategy,
    # choose the highest surviving current scanner result instead of keeping a
    # stale master rank.
    if row.get("scanner_best") == "best_opportunities":
        candidates = []
        for key, result in results.items():
            if not isinstance(result, dict):
                continue
            score = _n(result.get("score"))
            if score is not None:
                candidates.append((score, key))
        if candidates:
            score, key = max(candidates)
            row["scanner_best"] = key
            row["scanner_best_score"] = score
        else:
            row.pop("scanner_best", None)
            row.pop("scanner_best_score", None)


def _sanitize_carried(row: dict) -> None:
    for key in STALE_DERIVED_KEYS:
        row.pop(key, None)
    row["opportunity_score"] = None
    row["opportunity_score_raw"] = None
    row["opportunity_label"] = "Dados insuficientes"
    row["opportunity_eligible"] = False
    row["opportunity_suppressed_reason"] = "Linha sem atualização fundamental no run atual"
    row["opportunity_gates"] = []
    row["opportunity_caps"] = []
    row["scanner_tags"] = []
    row["scanner_results"] = {}
    # Preserve pure price-position information, but never an actionable low52
    # classification inherited from a stale row.
    if str(row.get("low52_status") or "").lower() in {"opportunity", "watch"}:
        row["low52_status"] = "insufficient"
        row["low52_label"] = "Dados insuficientes"
        row["low52_score"] = None
        row["low52_reason"] = "Dados fundamentais não atualizados no run atual"


def main() -> None:
    with open(STOCKS_PATH, "r", encoding="utf-8") as fh:
        payload = json.load(fh)

    rows = payload.get("stocks") or []
    refreshed = 0
    sanitized = 0

    for row in rows:
        if not isinstance(row, dict) or _is_fund(row):
            continue
        status = str(row.get("pipeline_status") or "")
        if status in {"equity_catalog_only", "equity_carried_forward"}:
            _sanitize_carried(row)
            sanitized += 1
            continue

        # Recalculate only the structural master rank. All source metrics and
        # ordinary scanner strategies remain untouched.
        row.update(assess_opportunity(row))
        _refresh_best_scanner(row)
        refreshed += 1

    payload["postprocess_market"] = {
        "opportunity_rows_refreshed": refreshed,
        "stale_rows_sanitized": sanitized,
        "same_run_recovery_used": True,
    }

    with open(STOCKS_PATH, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2, allow_nan=False)
        fh.write("\n")

    print(
        f"Postprocess complete: {refreshed} opportunity rows refreshed, "
        f"{sanitized} stale rows sanitized"
    )


if __name__ == "__main__":
    main()
