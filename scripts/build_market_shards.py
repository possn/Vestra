"""Build a lightweight market index plus full dossier shards from data/stocks.json.

stocks.json remains the validated source/fallback. The index contains only fields
needed before a dossier opens; full evidence/history stays in lazy dossier shards.
"""
from __future__ import annotations

import json
import os
import re
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "data", "stocks.json")
INDEX = os.path.join(ROOT, "data", "stocks-index.json")
SHARD_DIR = os.path.join(ROOT, "data", "dossiers")
MANIFEST = os.path.join(ROOT, "data", "dossiers-manifest.json")

# Explicit pre-dossier contract. Anything not listed here belongs to the dossier
# shard and is hydrated only when required. Keeping this list explicit prevents
# new enrichment scalars from silently bloating the startup payload again.
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
    # thesis / change signals
    "thesis_type", "thesis_slug", "thesis_confidence", "thesis_direction",
    "thesis_direction_label", "thesis_summary", "thesis_score_delta_7d",
    "estimate_signal", "estimate_momentum_score", "estimate_revision_score",
    # analyst / events used before dossier hydration
    "analyst_eps_revisions_up_30d", "analyst_eps_revisions_down_30d",
    "analyst_price_target_upside_pct", "analyst_next_earnings_date",
    "catalyst_next_date", "catalyst_risk_count", "catalyst_positive_count",
    # insiders / smart-money summaries
    "insider_status", "insider_buy_count_30d", "insider_sell_count_30d",
    "insider_buy_value_30d", "insider_sell_value_30d", "insider_net_value_30d",
    # opportunity / scanner summaries
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

# Scanner results remain pre-dossier data: the Scanner tab ranks/filter rows by
# these compact objects before a company dossier is opened.
SMALL_OBJECT_KEYS = {"scanner_results"}


def shard_for(ticker: str) -> str:
    c = (ticker or "_").strip().upper()[:1]
    return c if re.match(r"[A-Z0-9]", c) else "_"


def index_row(row: dict) -> dict:
    out = {k: row.get(k) for k in INDEX_KEYS if k in row}
    for k in SMALL_OBJECT_KEYS:
        v = row.get(k)
        if isinstance(v, dict):
            out[k] = v

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
    manifest = {}
    for ticker, row in rows:
        key = shard_for(ticker)
        shards[key][ticker] = row
        manifest[ticker] = key
        index_rows.append(index_row(row))

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
    print(
        f"market shards: {len(index_rows)} unique rows, {len(shards)} shards; "
        f"dropped {duplicate_count} duplicate rows; "
        f"index {idx_size/1_000_000:.2f} MB vs source {src_size/1_000_000:.2f} MB"
    )
    if len(index_rows) != len(manifest):
        raise RuntimeError("Market shard manifest/index cardinality mismatch")
    # Startup data should remain meaningfully smaller than the full dossier source.
    if src_size > 0 and idx_size >= src_size * 0.25:
        raise RuntimeError("Lightweight index is unexpectedly large (>=25% of stocks.json)")


if __name__ == "__main__":
    main()
