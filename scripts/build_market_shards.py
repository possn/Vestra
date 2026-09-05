"""Build compact market startup payloads plus full dossier shards.

stocks.json remains the validated source/fallback. The startup index contains only
fields required before a dossier opens. Scanner strategy results are emitted to a
separate lazy payload because they are needed only when the Scanner tool opens.
Full evidence/history remains in dossier shards.
"""
from __future__ import annotations

import json
import os
import re
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "data", "stocks.json")
INDEX = os.path.join(ROOT, "data", "stocks-index.json")
SCANNER_INDEX = os.path.join(ROOT, "data", "stocks-scanner.json")
SHARD_DIR = os.path.join(ROOT, "data", "dossiers")
MANIFEST = os.path.join(ROOT, "data", "dossiers-manifest.json")

# Startup performance budget. The historical 25% source-relative guard could
# silently allow the index to grow past 12 MB as stocks.json expands. Keep an
# absolute iPhone/PWA ceiling as well as a tighter relative ceiling so any future
# enrichment added to INDEX_KEYS requires an explicit architecture review.
MAX_INDEX_BYTES = 7_250_000
MAX_INDEX_RATIO = 0.15

# Explicit pre-dossier contract. Anything not listed here belongs to a lazy
# payload or dossier shard. Keeping this list explicit prevents new enrichment
# scalars from silently bloating startup again.
INDEX_KEYS = {
    # identity / search / filters
    "ticker", "name", "sector", "industry", "region", "country", "currency",
    "quote_type", "market_cap", "current_price", "zombie",
    # main score / evidence confidence
    "score", "data_confidence", "data_coverage_pct", "confidence_score",
    "confidence_label", "metric_confidence", "score_reliability", "risk_gate",
    "score_model",
    # dimensions used by list/portfolio ranking
    "quality_pct", "growth_pct", "balance_pct", "cashflow_pct", "value_pct",
    "execution_pct", "earnings_quality_pct", "capital_allocation_pct",
    "stability_pct", "profitability_pct", "leverage_pct",
    # compact valuation / portfolio fit
    "trailing_pe", "forward_pe", "price_to_book", "enterprise_to_ebitda",
    "forward_pe_vs_sector_pct", "trailing_pe_vs_sector_pct", "ev_ebitda_vs_sector_pct",
    "dividend_yield", "revenue_growth", "valuation_signal", "valuation_confidence",
    "fair_value_upside_pct", "margin_of_safety_pct",
    # thesis / change signals used by lists and watch snapshots
    "thesis_type", "thesis_confidence", "thesis_direction",
    "thesis_direction_label", "thesis_score_delta_7d",
    "estimate_signal", "estimate_momentum_score", "estimate_revision_score",
    # analyst / events used before dossier hydration
    "analyst_eps_revisions_up_30d", "analyst_eps_revisions_down_30d",
    "analyst_price_target_upside_pct", "analyst_next_earnings_date",
    "catalyst_next_date", "catalyst_risk_count", "catalyst_positive_count",
    # insiders / smart-money summaries
    "insider_status", "insider_buy_count_30d", "insider_sell_count_30d",
    "insider_buy_value_30d", "insider_sell_value_30d", "insider_net_value_30d",
    # opportunity summaries used outside the Scanner tool
    "scanner_best", "scanner_best_score", "qarp_score", "qarp_label",
    "opportunity_score", "opportunity_score_raw", "opportunity_label",
    "opportunity_eligible", "opportunity_signal_count", "opportunity_structural_signal_count",
    "opportunity_timing_score", "opportunity_timing_label", "opportunity_overextended",
    "opportunity_return_20d_pct", "opportunity_return_60d_pct",
    "opportunity_drawdown_from_high_pct",
    # low-52 / recovery / sector-relative summaries
    "low52_status", "low52_label", "low52_score", "low52_resilience_score",
    "low52_deterioration_penalty", "low52_above_low_pct", "low52_drawdown_from_high_pct",
    "low52_range_position_pct", "low52_price_low", "low52_price_high",
    "drawdown_diagnosis_status", "drawdown_primary_driver", "drawdown_primary_label",
    "drawdown_driver_trend", "sector_relative_peer_count", "return_1y_pct",
    "sector_median_return_1y_pct", "sector_relative_return_1y_pct",
    "sector_relative_drawdown_label", "sector_relative_drawdown_tone",
    "recovery_status", "recovery_label", "recovery_score", "recovery_price_score",
    "recovery_fundamental_score", "recovery_return_20d_pct", "recovery_return_60d_pct",
    # structural overlays used by ranking/portfolio UI
    "capital_allocation_intelligence_score", "capital_allocation_intelligence_label",
    "moat_score", "moat_label", "sector_native_score", "sector_native_label",
    "value_trap_risk_score", "value_trap_label",
    # fund list
    "expense_ratio", "fund_region", "fund_theme", "fund_style", "fund_ucits",
}

# Human-readable evidence belongs to the hydrated dossier, not the startup
# universe. Keeping this explicit makes the payload boundary testable and avoids
# reintroducing repeated strings for every asset during future enrichments.
DETAIL_ONLY_LIST_KEYS = {
    "data_sources", "opportunity_reasons", "opportunity_cautions",
    "scanner_reasons", "scanner_cautions", "thesis_reasons", "thesis_cautions",
}
DETAIL_ONLY_SCALAR_KEYS = {
    "thesis_slug", "thesis_summary",
}


def shard_for(ticker: str) -> str:
    c = (ticker or "_").strip().upper()[:1]
    return c if re.match(r"[A-Z0-9]", c) else "_"


def index_row(row: dict) -> dict:
    out = {k: row.get(k) for k in INDEX_KEYS if k in row}
    ticker = str(row.get("ticker") or "").upper()
    out["ticker"] = ticker
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
        out.setdefault("low52_price_low", min(closes))
        out.setdefault("low52_price_high", max(closes))
    return out


def scanner_results(row: dict) -> dict | None:
    value = row.get("scanner_results")
    return value if isinstance(value, dict) and value else None


def main() -> None:
    with open(SRC, "r", encoding="utf-8") as f:
        payload = json.load(f)
    source_rows = payload.get("stocks") or []
    generated_at = payload.get("generated_at")
    schema_version = payload.get("schema_version")

    # One canonical row per ticker. Last occurrence wins because late pipeline
    # stages may carry fresher enrichment than an earlier duplicate.
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
    scanner_tickers = {}
    manifest = {}
    for ticker, row in rows:
        key = shard_for(ticker)
        shards[key][ticker] = row
        manifest[ticker] = key
        index_rows.append(index_row(row))
        results = scanner_results(row)
        if results:
            scanner_tickers[ticker] = results

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

    # Keyed object avoids repeating the ticker field inside every scanner row and
    # can be merged into the already-loaded startup universe in O(n).
    with open(SCANNER_INDEX, "w", encoding="utf-8") as f:
        json.dump({
            "schema_version": schema_version,
            "generated_at": generated_at,
            "ticker_count": len(scanner_tickers),
            "tickers": scanner_tickers,
        }, f, ensure_ascii=False, separators=(",", ":"))

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
    scanner_size = os.path.getsize(SCANNER_INDEX)
    ratio = (idx_size / src_size) if src_size else 0
    print(
        f"market shards: {len(index_rows)} unique rows, {len(shards)} shards; "
        f"dropped {duplicate_count} duplicate rows; "
        f"index {idx_size/1_000_000:.2f} MB ({ratio:.1%} of source) + "
        f"lazy scanner {scanner_size/1_000_000:.2f} MB vs source {src_size/1_000_000:.2f} MB"
    )
    if len(index_rows) != len(manifest):
        raise RuntimeError("Market shard manifest/index cardinality mismatch")
    if len(scanner_tickers) > len(index_rows):
        raise RuntimeError("Scanner payload cardinality exceeds market index")
    if idx_size > MAX_INDEX_BYTES:
        raise RuntimeError(
            f"Market startup index exceeds absolute budget: {idx_size} > {MAX_INDEX_BYTES} bytes"
        )
    if src_size > 0 and ratio > MAX_INDEX_RATIO:
        raise RuntimeError(
            f"Market startup index exceeds relative budget: {ratio:.1%} > {MAX_INDEX_RATIO:.1%}"
        )


if __name__ == "__main__":
    main()
