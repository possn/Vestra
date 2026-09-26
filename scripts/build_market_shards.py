"""Build compact market startup payloads plus full dossier shards.

stocks.json remains the validated source/fallback. The startup index contains only
fields required before a dossier opens. Scanner strategy results are emitted to a
separate lazy payload because they are needed only when the Scanner tool opens.
Full evidence/history remains in dossier shards.
"""
from __future__ import annotations

import json
import math
import os
import re
import zlib
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "data", "stocks.json")
INDEX = os.path.join(ROOT, "data", "stocks-index.json")
COLUMNAR_INDEX = os.path.join(ROOT, "data", "stocks-startup.json")
SCANNER_INDEX = os.path.join(ROOT, "data", "stocks-scanner.json")
SHARD_DIR = os.path.join(ROOT, "data", "dossiers")
MANIFEST = os.path.join(ROOT, "data", "dossiers-manifest.json")
PORTFOLIO_SECTORS = os.path.join(ROOT, "data", "portfolio-sectors.json")
FUND_AUM_HISTORY = os.path.join(ROOT, "data", "fund-aum-history.json")
FUND_FLOW_HISTORY_DAYS = 120
FUND_FLOW_MIN_DAYS = 5
FUND_FLOW_MAX_DAYS = 14

# Startup performance budgets. The browser now prefers COLUMNAR_INDEX and falls
# back to INDEX/SRC only when the compact payload is unavailable or invalid.
# Keep both representations bounded: INDEX protects compatibility/fallback cost;
# COLUMNAR_INDEX protects the normal iPhone/PWA startup path. The first canonical
# production snapshot measured 1,958,111 bytes vs a 6,595,930-byte index (29.7%).
MAX_INDEX_BYTES = 7_250_000
MAX_INDEX_RATIO = 0.15
MAX_COLUMNAR_BYTES = 2_250_000
MAX_COLUMNAR_INDEX_RATIO = 0.35
# Regression floor for the field_rows_v1 columnar codec. Observed savings on the
# current universe are ~0.70; 0.5 leaves headroom before the codec would need
# revisiting (e.g. universe shrinks, or more per-row fields become dense).
MIN_COLUMNAR_SAVING_RATIO = 0.5

# Full dossier payloads used to be grouped only by the first ticker character.
# A/C/M-class shards can reach several MB and JSON.parse then competes with the
# open dossier on Safari/iPhone. Keep the human-readable prefix but distribute
# each prefix across a small deterministic set of buckets. The manifest remains
# authoritative, so the browser loader needs no routing change.
SHARD_BUCKETS = 4

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
    "opportunity_return_5d_pct", "opportunity_return_20d_pct", "opportunity_return_60d_pct",
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
    "expense_ratio", "fund_total_assets", "fund_region", "fund_theme", "fund_style", "fund_ucits",
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
    raw = (ticker or "_").strip().upper() or "_"
    c = raw[:1]
    prefix = c if re.match(r"[A-Z0-9]", c) else "_"
    bucket = zlib.crc32(raw.encode("utf-8")) % SHARD_BUCKETS
    return f"{prefix}{bucket}"


def _finite_positive(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) and value > 0 else None


def load_fund_aum_history(path: str = FUND_AUM_HISTORY) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            value = json.load(f)
        return value if isinstance(value, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def update_fund_aum_history(rows: list[dict], as_of: str, history: dict | None = None) -> dict:
    history = history if isinstance(history, dict) else {}
    day = str(as_of or "")[:10]
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", day):
        return history
    for row in rows:
        if str(row.get("quote_type") or "").upper() not in {"ETF", "MUTUALFUND", "FUND"}:
            continue
        ticker = str(row.get("ticker") or "").strip().upper()
        assets = _finite_positive(row.get("fund_total_assets"))
        price = _finite_positive(row.get("current_price"))
        if not ticker or assets is None or price is None:
            continue
        series = history.setdefault(ticker, {})
        series[day] = {"assets": round(assets, 2), "price": round(price, 6)}
        for old_day in sorted(series)[:-FUND_FLOW_HISTORY_DAYS]:
            del series[old_day]
    return history


def fund_weekly_return(row: dict):
    hist = row.get("price_history_1y") or []
    points = []
    for item in hist:
        if not isinstance(item, dict):
            continue
        close = _finite_positive(item.get("close"))
        day = str(item.get("date") or "")[:10]
        if close is not None and day:
            points.append((day, close))
    if len(points) < 2:
        return None
    points.sort(key=lambda x: x[0])
    previous, current = points[-2], points[-1]
    if previous[1] <= 0:
        return None
    return round((current[1] / previous[1] - 1.0) * 100.0, 3)


def fund_flow_metrics(row: dict, history: dict, as_of: str) -> dict:
    result = {}
    week_return = fund_weekly_return(row)
    if week_return is not None:
        result["fund_return_1w_pct"] = week_return
    ticker = str(row.get("ticker") or "").strip().upper()
    day = str(as_of or "")[:10]
    series = history.get(ticker) if isinstance(history, dict) else None
    if not ticker or not day or not isinstance(series, dict) or day not in series:
        return result
    try:
        current_date = __import__("datetime").date.fromisoformat(day)
    except ValueError:
        return result
    candidates = []
    for prior_day, point in series.items():
        if prior_day == day or not isinstance(point, dict):
            continue
        try:
            prior_date = __import__("datetime").date.fromisoformat(prior_day)
        except ValueError:
            continue
        gap = (current_date - prior_date).days
        if FUND_FLOW_MIN_DAYS <= gap <= FUND_FLOW_MAX_DAYS:
            candidates.append((abs(gap - 7), -gap, prior_day, point))
    if not candidates:
        return result
    _, neg_gap, prior_day, previous = sorted(candidates)[0]
    current = series.get(day) or {}
    current_assets = _finite_positive(current.get("assets"))
    prior_assets = _finite_positive(previous.get("assets"))
    current_price = _finite_positive(current.get("price"))
    prior_price = _finite_positive(previous.get("price"))
    if None in {current_assets, prior_assets, current_price, prior_price}:
        return result
    price_ratio = current_price / prior_price
    expected_assets_without_flow = prior_assets * price_ratio
    flow_usd = current_assets - expected_assets_without_flow
    flow_pct = flow_usd / expected_assets_without_flow * 100.0 if expected_assets_without_flow > 0 else None
    if flow_pct is None or not math.isfinite(flow_pct):
        return result
    result.update({
        "fund_flow_1w_pct": round(flow_pct, 3),
        "fund_flow_1w_usd": round(flow_usd, 2),
        "fund_flow_observation_days": -neg_gap,
        "fund_flow_reference_date": prior_day,
    })
    return result


def index_row(row: dict, fund_history: dict | None = None, as_of: str = "") -> dict:
    out = {k: row.get(k) for k in INDEX_KEYS if k in row}
    ticker = str(row.get("ticker") or "").upper()
    out["ticker"] = ticker
    out["dossier_shard"] = shard_for(ticker)

    # Funds need concentration before dossier hydration, but the complete holdings
    # list remains in the lazy dossier. Keep only the top-10 aggregate in startup.
    holdings = row.get("top_holdings")
    if isinstance(holdings, list) and holdings:
        weights = []
        for holding in holdings[:10]:
            if not isinstance(holding, dict):
                continue
            raw = next((holding.get(k) for k in ("holdingPercent", "weight", "pct", "percentage") if holding.get(k) is not None), None)
            try:
                value = float(raw)
            except (TypeError, ValueError):
                continue
            if not math.isfinite(value) or value < 0:
                continue
            weights.append(value * 100 if abs(value) <= 1 else value)
        if weights:
            out["fund_top10_weight_pct"] = round(sum(weights), 6)

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
    if str(row.get("quote_type") or "").upper() in {"ETF", "MUTUALFUND", "FUND"}:
        out.update(fund_flow_metrics(row, fund_history or {}, as_of))
    return out


def pack_index_payload(index_payload: dict) -> dict:
    """Dictionary-code repeated row keys while preserving all startup values."""
    rows = index_payload.get("stocks") or []
    frequency: dict[str, int] = defaultdict(int)
    for row in rows:
        if not isinstance(row, dict):
            continue
        for key in row:
            frequency[key] += 1

    # Common fields first means sparse fields tend to the tail; trailing nulls can
    # then be removed from each row without a bitmap or per-row key list.
    fields = sorted(frequency, key=lambda key: (-frequency[key], key))
    packed_rows = []
    for row in rows:
        values = [row.get(field) if field in row else None for field in fields]
        while values and values[-1] is None:
            values.pop()
        packed_rows.append(values)

    meta = {k: v for k, v in index_payload.items() if k != "stocks"}
    return {
        **meta,
        "layout": "field_rows_v1",
        "fields": fields,
        "rows": packed_rows,
    }


def unpack_index_payload(packed: dict) -> dict:
    """Reference decoder used by tests and mirrored by the browser loader."""
    if packed.get("layout") != "field_rows_v1":
        return packed
    fields = packed.get("fields") or []
    rows = packed.get("rows") or []
    stocks = []
    for values in rows:
        if not isinstance(values, list):
            continue
        stocks.append({field: values[i] for i, field in enumerate(fields[:len(values)])})
    meta = {k: v for k, v in packed.items() if k not in {"layout", "fields", "rows"}}
    return {**meta, "stocks": stocks}


def scanner_results(row: dict) -> dict | None:
    value = row.get("scanner_results")
    return value if isinstance(value, dict) and value else None


def portfolio_sector_row(row: dict) -> dict | None:
    """Return only the identity fields needed by the portfolio sector card."""
    sector = str(row.get("sector") or "").strip()
    if not sector:
        return None
    result = {"sector": sector}
    industry = str(row.get("industry") or "").strip()
    quote_type = str(row.get("quote_type") or "").strip()
    if industry:
        result["industry"] = industry
    if quote_type:
        result["quote_type"] = quote_type
    return result


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
    fund_history = update_fund_aum_history(
        [row for _, row in rows],
        str(generated_at or "")[:10],
        load_fund_aum_history(),
    )

    shards: dict[str, dict[str, dict]] = defaultdict(dict)
    index_rows = []
    scanner_tickers = {}
    portfolio_sectors = {}
    manifest = {}
    for ticker, row in rows:
        key = shard_for(ticker)
        shards[key][ticker] = row
        manifest[ticker] = key
        index_rows.append(index_row(row, fund_history, str(generated_at or "")[:10]))
        results = scanner_results(row)
        if results:
            scanner_tickers[ticker] = results
        sector_row = portfolio_sector_row(row)
        if sector_row:
            portfolio_sectors[ticker] = sector_row

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

    with open(FUND_AUM_HISTORY, "w", encoding="utf-8") as f:
        json.dump(fund_history, f, ensure_ascii=False, separators=(",", ":"))

    # Production startup representation. market-static-universe.js prefers this
    # field/rows payload and falls back to INDEX then SRC if it is unavailable or
    # invalid, so the compact file is now the normal transfer path on iPhone/PWA.
    packed_payload = pack_index_payload(index_payload)
    with open(COLUMNAR_INDEX, "w", encoding="utf-8") as f:
        json.dump(packed_payload, f, ensure_ascii=False, separators=(",", ":"))

    # Keyed object avoids repeating the ticker field inside every scanner row and
    # can be merged into the already-loaded startup universe in O(n).
    with open(SCANNER_INDEX, "w", encoding="utf-8") as f:
        json.dump({
            "schema_version": schema_version,
            "generated_at": generated_at,
            "ticker_count": len(scanner_tickers),
            "tickers": scanner_tickers,
        }, f, ensure_ascii=False, separators=(",", ":"))

    # Small on-demand identity map for the Carteira sector view. Loading the
    # full Market startup universe here would make a portfolio-only action pay
    # the 2 MB Market bootstrap cost.
    with open(PORTFOLIO_SECTORS, "w", encoding="utf-8") as f:
        json.dump({
            "schema_version": schema_version,
            "generated_at": generated_at,
            "ticker_count": len(portfolio_sectors),
            "tickers": portfolio_sectors,
        }, f, ensure_ascii=False, separators=(",", ":"))

    shard_sizes = {}
    for key, values in sorted(shards.items()):
        path = os.path.join(SHARD_DIR, f"{key}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"schema_version": schema_version, "generated_at": generated_at, "shard": key, "stocks": values}, f, ensure_ascii=False, separators=(",", ":"))
        shard_sizes[key] = os.path.getsize(path)

    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump({
            "schema_version": schema_version,
            "generated_at": generated_at,
            "ticker_count": len(manifest),
            "duplicate_rows_dropped": duplicate_count,
            "shard_buckets_per_prefix": SHARD_BUCKETS,
            "tickers": manifest,
        }, f, ensure_ascii=False, separators=(",", ":"))

    src_size = os.path.getsize(SRC)
    idx_size = os.path.getsize(INDEX)
    columnar_size = os.path.getsize(COLUMNAR_INDEX)
    scanner_size = os.path.getsize(SCANNER_INDEX)
    ratio = (idx_size / src_size) if src_size else 0
    columnar_index_ratio = (columnar_size / idx_size) if idx_size else 0
    saving_ratio = 1 - columnar_index_ratio if idx_size else 0
    max_shard_name, max_shard_size = max(shard_sizes.items(), key=lambda item: item[1], default=("", 0))
    print(
        f"market shards: {len(index_rows)} unique rows, {len(shards)} shards; "
        f"dropped {duplicate_count} duplicate rows; "
        f"largest shard {max_shard_name or 'n/a'} {max_shard_size/1_000_000:.2f} MB; "
        f"index {idx_size/1_000_000:.2f} MB ({ratio:.1%} of source); "
        f"columnar {columnar_size/1_000_000:.2f} MB ({saving_ratio:.1%} smaller); "
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
    if columnar_size > MAX_COLUMNAR_BYTES:
        raise RuntimeError(
            f"Columnar startup payload exceeds absolute budget: {columnar_size} > {MAX_COLUMNAR_BYTES} bytes"
        )
    if idx_size > 0 and columnar_index_ratio > MAX_COLUMNAR_INDEX_RATIO:
        raise RuntimeError(
            f"Columnar startup payload exceeds index-relative budget: "
            f"{columnar_index_ratio:.1%} > {MAX_COLUMNAR_INDEX_RATIO:.1%}"
        )


if __name__ == "__main__":
    main()
