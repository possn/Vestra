"""Shadow evaluation of peer-first normalization for specialist Vestra score packs.

Phase 1 covers banks because their current pack still derives most percentile inputs
from the global equity universe. The production score is never modified. The output
only quantifies how much the same weights/risk caps would move if bank metrics were
ranked against bank peers whenever at least 20 finite observations exist.
"""
from __future__ import annotations

import datetime as dt
import json
import math
from pathlib import Path

from peer_benchmark import peer_first_percentile

ROOT = Path(__file__).resolve().parents[1]
STOCKS = ROOT / "data" / "stocks.json"
OUT = ROOT / "data" / "score_peer_shadow.json"
MIN_PEERS = 20


def n(v):
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def avg(values):
    vals = [n(v) for v in values]
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals) if vals else None


def weighted(parts):
    usable = [(n(v), w) for v, w in parts]
    usable = [(v, w) for v, w in usable if v is not None]
    if not usable:
        return None
    den = sum(w for _, w in usable)
    return sum(v * w for v, w in usable) / den if den else None


def pct(row, field, peers, all_rows, *, invert=False):
    result = peer_first_percentile(
        row.get(field),
        (x.get(field) for x in peers),
        (x.get(field) for x in all_rows),
        invert=invert,
        min_peers=MIN_PEERS,
    )
    return result.score, result.scope, result.peer_observations


def growth_score(row, peers, all_rows):
    values = []
    meta = []
    for field in ("revenue_growth", "earnings_growth", "earnings_quarterly_growth"):
        score, scope, count = pct(row, field, peers, all_rows)
        values.append(score)
        meta.append((field, scope, count))
    return avg(values), meta


def bank_shadow(row, peers, all_rows):
    scopes = []

    def p(field, invert=False):
        score, scope, count = pct(row, field, peers, all_rows, invert=invert)
        scopes.append({"metric": field, "scope": scope, "peer_observations": count})
        return score

    bank_quality = avg([p("roe"), p("roa"), p("profit_margin")])
    bank_efficiency = p("efficiency_ratio_proxy", True)
    bank_asset_quality = p("provision_to_revenue", True)
    bank_capital = p("equity_to_assets")
    base_growth, growth_meta = growth_score(row, peers, all_rows)
    scopes.extend({"metric": f, "scope": s, "peer_observations": c} for f, s, c in growth_meta)
    bank_nii_growth = p("net_interest_income_yoy")
    bank_growth = avg([base_growth, bank_nii_growth])

    value_parts = []
    for field in ("price_to_book", "trailing_pe", "forward_pe"):
        raw = n(row.get(field))
        value_parts.append(p(field, True) if raw is not None and raw > 0 else None)
    bank_value = avg(value_parts)
    income = p("dividend_yield")
    stability = p("beta", True)

    composite = weighted([
        (bank_quality, .22),
        (bank_efficiency, .13),
        (bank_asset_quality, .10),
        (bank_capital, .15),
        (bank_growth, .15),
        (bank_value, .15),
        (income, .05),
        (stability, .05),
    ])
    cap = n(row.get("score_cap"))
    if composite is not None and cap is not None:
        composite = min(composite, cap)
    return composite, {
        "Bank Quality": bank_quality,
        "Efficiency": bank_efficiency,
        "Asset Quality": bank_asset_quality,
        "Capital Proxy": bank_capital,
        "Growth": bank_growth,
        "Valuation": bank_value,
        "Income": income,
        "Stability": stability,
    }, scopes


def rank_map(rows, field):
    ordered = sorted(
        ((str(r.get("ticker")), n(r.get(field))) for r in rows if n(r.get(field)) is not None),
        key=lambda x: x[1], reverse=True,
    )
    return {ticker: i + 1 for i, (ticker, _) in enumerate(ordered)}


def main():
    payload = json.loads(STOCKS.read_text(encoding="utf-8"))
    rows = [r for r in (payload.get("stocks") or []) if isinstance(r, dict)]
    equities = [
        r for r in rows
        if str(r.get("quote_type") or "").upper() not in {"ETF", "CRYPTO", "FUND", "MUTUALFUND"}
        and str(r.get("pipeline_status") or "") not in {"equity_catalog_only", "equity_carried_forward"}
    ]
    banks = [r for r in equities if str(r.get("score_model") or "") == "bank" and n(r.get("score")) is not None]

    shadow_rows = []
    for row in banks:
        shadow, dims, scopes = bank_shadow(row, banks, equities)
        if shadow is None:
            continue
        production = n(row.get("score"))
        shadow_rows.append({
            "ticker": row.get("ticker"),
            "name": row.get("name"),
            "sector": row.get("sector"),
            "production_score": production,
            "peer_shadow_score": round(shadow, 2),
            "delta": round(shadow - production, 2) if production is not None else None,
            "score_cap": row.get("score_cap"),
            "shadow_dimensions": {k: (round(v, 2) if v is not None else None) for k, v in dims.items()},
            "benchmark_scopes": scopes,
        })

    prod_rank = {ticker: i + 1 for i, (ticker, _) in enumerate(sorted(
        ((str(x.get("ticker")), n(x.get("score"))) for x in banks if n(x.get("score")) is not None),
        key=lambda x: x[1], reverse=True,
    ))}
    shadow_rank = {ticker: i + 1 for i, (ticker, _) in enumerate(sorted(
        ((str(x.get("ticker")), n(x.get("peer_shadow_score"))) for x in shadow_rows if n(x.get("peer_shadow_score")) is not None),
        key=lambda x: x[1], reverse=True,
    ))}
    for item in shadow_rows:
        ticker = str(item.get("ticker"))
        item["production_bank_rank"] = prod_rank.get(ticker)
        item["shadow_bank_rank"] = shadow_rank.get(ticker)
        if item["production_bank_rank"] and item["shadow_bank_rank"]:
            item["rank_shift"] = item["production_bank_rank"] - item["shadow_bank_rank"]

    deltas = [n(x.get("delta")) for x in shadow_rows]
    deltas = [x for x in deltas if x is not None]
    scope_counts = {"peer_model": 0, "global_fallback": 0}
    for item in shadow_rows:
        for meta in item["benchmark_scopes"]:
            scope = meta.get("scope")
            if scope in scope_counts:
                scope_counts[scope] += 1

    most_changed = sorted(shadow_rows, key=lambda x: abs(n(x.get("delta")) or 0), reverse=True)[:25]
    rank_changed = sorted(shadow_rows, key=lambda x: abs(n(x.get("rank_shift")) or 0), reverse=True)[:25]
    out = {
        "schema_version": 1,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "production_unchanged": True,
        "phase": "bank_peer_normalization_shadow",
        "methodology": {
            "weights": {"quality":.22,"efficiency":.13,"asset_quality":.10,"capital":.15,"growth":.15,"valuation":.15,"income":.05,"stability":.05},
            "min_peer_observations": MIN_PEERS,
            "fallback": "global equity universe when fewer than 20 finite bank observations exist",
            "risk_caps": "existing production score_cap is applied unchanged",
        },
        "bank_rows": len(banks),
        "shadow_rows": len(shadow_rows),
        "mean_delta": round(sum(deltas) / len(deltas), 3) if deltas else None,
        "mean_absolute_delta": round(sum(abs(x) for x in deltas) / len(deltas), 3) if deltas else None,
        "max_absolute_delta": round(max((abs(x) for x in deltas), default=0), 3),
        "benchmark_scope_counts": scope_counts,
        "most_changed_scores": most_changed,
        "largest_bank_rank_shifts": rank_changed,
        "rows": shadow_rows,
        "activation_rule": "Do not activate peer-first bank scoring from this file alone. Review sample depth, score/rank displacement and prospective validation first.",
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Bank peer shadow: {len(shadow_rows)}/{len(banks)} rows; mean |delta|={out['mean_absolute_delta']}; max |delta|={out['max_absolute_delta']}")


if __name__ == "__main__":
    main()
