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
import re
import statistics

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
    "opportunity_upside_support",
    "opportunity_upside_reasons",
    "opportunity_eligible",
    "opportunity_suppressed_reason",
    "opportunity_signal_count",
    "opportunity_structural_signal_count",
    "opportunity_gates",
    "opportunity_caps",
    "opportunity_rotation_theme",
    "opportunity_rotation_signal",
    "opportunity_rotation_breadth_pct",
    "opportunity_rotation_return_5d_pct",
    "opportunity_rotation_etf_confirmed",
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


ROTATION_THEMES = [
    ("Semicondutores", re.compile(r"semiconductor|semiconductors|chip|foundry|wafer|integrated circuit", re.I), ("SMH","SOXX","XSD")),
    ("Biotecnologia", re.compile(r"biotech|biotechnology|genomic|genomics|gene therap|life sciences", re.I), ("XBI","IBB","ARKG")),
    ("Minerais & metais", re.compile(r"metal|mining|miner|copper|lithium|uranium|gold|silver|steel|aluminum|aluminium|rare earth", re.I), ("COPX","PICK")),
    ("Agricultura", re.compile(r"agricultur|agribusiness|farm|crop|seed|fertili[sz]er|grain|potash", re.I), ()),
    ("Energia", re.compile(r"energy|oil|gas|petroleum|exploration|drilling|refin", re.I), ("XLE","XOP")),
    ("Defesa & aeroespacial", re.compile(r"defen[cs]e|aerospace|military|weapon|missile", re.I), ("ITA","PPA","XAR")),
    ("IA & software", re.compile(r"artificial intelligence|machine learning|software|cloud|saas|cyber|data infrastructure", re.I), ("IGV","AIQ","BOTZ","CHAT","WCLD")),
    ("Bancos", re.compile(r"bank|banks|banking|financial services", re.I), ("KBE","KRE","XLF")),
    ("Imobiliário", re.compile(r"real estate|reit|property", re.I), ("VNQ","IYR","XLRE")),
    ("Consumo discricionário", re.compile(r"consumer cyclical|consumer discretionary|auto manufacturer|travel|leisure|retail", re.I), ("XLY","VCR")),
]


def _weekly_return(row: dict):
    published = _n(row.get("opportunity_return_5d_pct"))
    if published is not None:
        return published
    hist = row.get("price_history_1y") or []
    closes = [_n(x.get("close")) for x in hist if isinstance(x, dict)]
    closes = [x for x in closes if x is not None and x > 0]
    if len(closes) <= 5:
        return None
    return (closes[-1] / closes[-6] - 1.0) * 100.0


def _rotation_context(rows):
    equities = [r for r in rows if isinstance(r, dict) and not _is_fund(r)]
    by_ticker = {str(r.get("ticker") or "").upper(): r for r in rows if isinstance(r, dict)}
    contexts = {}
    for label, pattern, etfs in ROTATION_THEMES:
        members = [r for r in equities if pattern.search(" ".join(str(r.get(k) or "") for k in ("sector","industry","name")))]
        weekly = [(r, _weekly_return(r)) for r in members]
        weekly = [(r, ret) for r, ret in weekly if ret is not None]
        if len(weekly) < 4:
            continue
        returns = [ret for _, ret in weekly]
        med5 = statistics.median(returns)
        breadth = sum(1 for ret in returns if ret > 0) / len(returns) * 100.0
        if med5 >= 2 and breadth >= 60:
            signal = "strong_inflow"
        elif med5 >= .5 and breadth >= 55:
            signal = "inflow"
        elif med5 <= -2 and breadth <= 40:
            signal = "strong_outflow"
        elif med5 <= -.5 and breadth <= 45:
            signal = "outflow"
        else:
            signal = "mixed"

        etf_rows = [by_ticker.get(t) for t in etfs]
        etf_rows = [x for x in etf_rows if isinstance(x, dict)]
        etf_returns = [_n(x.get("fund_return_1w_pct")) for x in etf_rows]
        etf_returns = [x for x in etf_returns if x is not None]
        etf_flows = [_n(x.get("fund_flow_1w_usd")) for x in etf_rows]
        etf_flows = [x for x in etf_flows if x is not None]
        etf_return = statistics.median(etf_returns) if etf_returns else None
        etf_flow = sum(etf_flows) if etf_flows else None
        etf_confirmed = None
        if signal in {"strong_inflow","inflow"} and (etf_return is not None or etf_flow is not None):
            etf_confirmed = bool((etf_return is not None and etf_return > 0) or (etf_flow is not None and etf_flow > 0))
        elif signal in {"strong_outflow","outflow"} and (etf_return is not None or etf_flow is not None):
            etf_confirmed = bool((etf_return is not None and etf_return < 0) or (etf_flow is not None and etf_flow < 0))
        contexts[label] = {
            "signal": signal,
            "median_return_5d_pct": round(med5, 2),
            "breadth_pct": round(breadth, 1),
            "member_count": len(weekly),
            "etf_confirmed": etf_confirmed,
        }
    return contexts


def _attach_rotation_context(row: dict, contexts: dict) -> None:
    haystack = " ".join(str(row.get(k) or "") for k in ("sector","industry","name"))
    matched = next(((label, ctx) for label, pattern, _ in ROTATION_THEMES if pattern.search(haystack) for ctx in [contexts.get(label)] if ctx), None)
    if not matched:
        for key in ("opportunity_rotation_theme","opportunity_rotation_signal","opportunity_rotation_breadth_pct","opportunity_rotation_return_5d_pct","opportunity_rotation_etf_confirmed"):
            row.pop(key, None)
        return
    label, ctx = matched
    row["opportunity_rotation_theme"] = label
    row["opportunity_rotation_signal"] = ctx["signal"]
    row["opportunity_rotation_breadth_pct"] = ctx["breadth_pct"]
    row["opportunity_rotation_return_5d_pct"] = ctx["median_return_5d_pct"]
    row["opportunity_rotation_etf_confirmed"] = ctx["etf_confirmed"]


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
    rotation_contexts = _rotation_context(rows)

    for row in rows:
        if not isinstance(row, dict) or _is_fund(row):
            continue
        status = str(row.get("pipeline_status") or "")
        if status in {"equity_catalog_only", "equity_carried_forward"}:
            _sanitize_carried(row)
            sanitized += 1
            continue

        # Attach same-run market-rotation context before recalculating the
        # structural master rank. Rotation may constrain timing, never add alpha.
        _attach_rotation_context(row, rotation_contexts)
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
