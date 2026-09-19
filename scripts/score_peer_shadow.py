"""Peer-first shadow candidates for specialist Vestra score packs.

This module never changes production scores. It rebuilds specialist score packs
with the same production weights and structural risk caps, but ranks each raw
metric against peers from the same score model whenever at least MIN_PEERS
finite observations exist. Sparse metrics fall back to the global equity
universe. The output is consumed by prospective validation only.
"""
from __future__ import annotations

import datetime as dt
import json
import math
from collections import defaultdict
from pathlib import Path

from peer_benchmark import peer_first_percentile

ROOT = Path(__file__).resolve().parents[1]
STOCKS = ROOT / "data" / "stocks.json"
OUT = ROOT / "data" / "score_peer_shadow.json"
MIN_PEERS = 20
SPECIALIST_MODELS = ("bank", "reit", "insurance", "utility", "energy", "biotech", "growth_tech")


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


def positive_score(value):
    value = n(value)
    if value is None:
        return None
    return 100.0 if value > 0 else 0.0


def raw_score(row):
    value = n(row.get("score_raw"))
    return value if value is not None else n(row.get("score"))


def apply_cap(value, row):
    value = n(value)
    cap = n(row.get("score_cap"))
    if value is None:
        return None
    return min(value, cap) if cap is not None else value


def ratio(row, numerator, denominator):
    a = n(row.get(numerator))
    b = n(row.get(denominator))
    return a / b if a is not None and b not in (None, 0) else None


def plausible_fcf_yield(row):
    value = n(row.get("fcf_yield"))
    if value is None or abs(value) > 0.30:
        return None
    return value


class ShadowContext:
    def __init__(self, row, peers, all_rows):
        self.row = row
        self.peers = peers
        self.all_rows = all_rows
        self.scopes = []

    def value(self, metric, value, peer_values, global_values, *, invert=False):
        result = peer_first_percentile(
            value,
            peer_values,
            global_values,
            invert=invert,
            min_peers=MIN_PEERS,
        )
        self.scopes.append({
            "metric": metric,
            "scope": result.scope,
            "peer_observations": result.peer_observations,
        })
        return result.score

    def p(self, field, invert=False, *, positive_only=False):
        value = n(self.row.get(field))
        if positive_only and (value is None or value <= 0):
            self.scopes.append({
                "metric": field,
                "scope": "missing",
                "peer_observations": sum(
                    1 for x in self.peers if n(x.get(field)) is not None and n(x.get(field)) > 0
                ),
            })
            return None
        peer_values = [
            n(x.get(field))
            for x in self.peers
            if not positive_only or (n(x.get(field)) is not None and n(x.get(field)) > 0)
        ]
        global_values = [
            n(x.get(field))
            for x in self.all_rows
            if not positive_only or (n(x.get(field)) is not None and n(x.get(field)) > 0)
        ]
        return self.value(field, value, peer_values, global_values, invert=invert)

    def derived(self, metric, fn, *, invert=False):
        return self.value(
            metric,
            fn(self.row),
            [fn(x) for x in self.peers],
            [fn(x) for x in self.all_rows],
            invert=invert,
        )

    def growth(self):
        return avg([
            self.p("revenue_growth"),
            self.p("earnings_growth"),
            self.p("earnings_quarterly_growth"),
        ])

    def stability(self):
        return self.p("beta", invert=True)

    def income(self):
        return self.p("dividend_yield")

    def interest_coverage(self):
        return self.p("interest_coverage")

    def net_cash_to_cap(self):
        return self.derived(
            "net_cash_to_market_cap",
            lambda x: (
                n(x.get("net_cash")) / n(x.get("market_cap"))
                if n(x.get("net_cash")) is not None and n(x.get("market_cap")) not in (None, 0)
                else None
            ),
        )

    def cashflow(self):
        return avg([
            self.value(
                "fcf_yield",
                plausible_fcf_yield(self.row),
                [plausible_fcf_yield(x) for x in self.peers],
                [plausible_fcf_yield(x) for x in self.all_rows],
            ),
            positive_score(self.row.get("operating_cash_flow")),
        ])

    def quality(self):
        return avg([
            self.p("roe"),
            self.p("roa"),
            self.p("profit_margin"),
            self.p("operating_margin"),
            self.p("gross_margin"),
        ])

    def balance(self):
        return avg([
            self.p("current_ratio"),
            self.p("quick_ratio"),
            self.p("debt_to_equity", invert=True),
            self.net_cash_to_cap(),
            self.interest_coverage(),
        ])


def bank_shadow(ctx):
    quality = avg([ctx.p("roe"), ctx.p("roa"), ctx.p("profit_margin")])
    efficiency = ctx.p("efficiency_ratio_proxy", invert=True)
    asset_quality = ctx.p("provision_to_revenue", invert=True)
    capital = ctx.p("equity_to_assets")
    growth = avg([ctx.growth(), ctx.p("net_interest_income_yoy")])
    value = avg([
        ctx.p("price_to_book", invert=True, positive_only=True),
        ctx.p("trailing_pe", invert=True, positive_only=True),
        ctx.p("forward_pe", invert=True, positive_only=True),
    ])
    income = ctx.income()
    stability = ctx.stability()
    score = weighted([
        (quality, .22), (efficiency, .13), (asset_quality, .10), (capital, .15),
        (growth, .15), (value, .15), (income, .05), (stability, .05),
    ])
    return score, {
        "Bank Quality": quality, "Efficiency": efficiency, "Asset Quality": asset_quality,
        "Capital Proxy": capital, "Growth": growth, "Valuation": value,
        "Income": income, "Stability": stability,
    }


def reit_shadow(ctx):
    quality = avg([
        ctx.p("reit_ffo_per_share_proxy"),
        ctx.p("roe"),
        ctx.p("profit_margin"),
    ])
    leverage = avg([
        ctx.p("reit_net_debt_to_ebitda", invert=True),
        ctx.interest_coverage(),
    ])
    value = avg([
        ctx.p("reit_p_ffo_proxy", invert=True, positive_only=True),
        ctx.p("price_to_book", invert=True, positive_only=True),
    ])
    distribution = avg([
        ctx.income(),
        ctx.p("reit_ffo_payout_proxy", invert=True),
    ])
    growth = ctx.growth()
    stability = ctx.stability()
    score = weighted([
        (quality, .22), (growth, .16), (leverage, .20),
        (value, .20), (distribution, .17), (stability, .05),
    ])
    return score, {
        "REIT Quality": quality, "Growth": growth, "Leverage": leverage,
        "P/FFO Value": value, "Distribution": distribution, "Stability": stability,
    }


def insurance_shadow(ctx):
    quality = avg([ctx.p("roe"), ctx.p("roa"), ctx.p("profit_margin")])
    underwriting = avg([
        ctx.p("insurance_claims_to_revenue", invert=True),
        ctx.p("insurance_operating_ratio_proxy", invert=True),
    ])
    capital = avg([
        ctx.p("insurance_equity_to_assets"),
        ctx.p("debt_to_equity", invert=True),
    ])
    value = avg([
        ctx.p("price_to_book", invert=True, positive_only=True),
        ctx.p("trailing_pe", invert=True, positive_only=True),
    ])
    income = avg([
        ctx.income(),
        positive_score(ctx.row.get("insurance_net_investment_income")),
    ])
    growth = ctx.growth()
    stability = ctx.stability()
    score = weighted([
        (quality, .22), (underwriting, .18), (capital, .18), (growth, .12),
        (value, .17), (income, .08), (stability, .05),
    ])
    return score, {
        "Insurance Quality": quality, "Underwriting Proxy": underwriting,
        "Capital Proxy": capital, "Growth": growth, "Valuation": value,
        "Income": income, "Stability": stability,
    }


def utility_shadow(ctx):
    quality = avg([ctx.p("roe"), ctx.p("operating_margin"), ctx.p("roce_proxy")])
    balance = avg([ctx.p("debt_to_equity", invert=True), ctx.interest_coverage()])
    income = avg([
        ctx.income(),
        ctx.p("payout_ratio", invert=True),
    ])
    value = avg([
        ctx.p("forward_pe", invert=True, positive_only=True),
        ctx.p("trailing_pe", invert=True, positive_only=True),
        ctx.p("price_to_book", invert=True, positive_only=True),
    ])
    base_cash = ctx.cashflow()
    cashflow = avg([base_cash, positive_score(ctx.row.get("operating_cash_flow"))])
    growth = ctx.growth()
    stability = ctx.stability()
    score = weighted([
        (quality, .18), (balance, .22), (income, .18), (value, .17),
        (growth, .10), (stability, .10), (cashflow, .05),
    ])
    return score, {
        "Utility Quality": quality, "Balance": balance, "Income": income,
        "Valuation": value, "Growth": growth, "Stability": stability,
        "Cash Flow": cashflow,
    }


def energy_shadow(ctx):
    quality = avg([ctx.p("roe"), ctx.p("operating_margin"), ctx.p("roce_proxy")])
    cashflow = ctx.cashflow()
    balance = avg([
        ctx.p("debt_to_equity", invert=True),
        ctx.net_cash_to_cap(),
        ctx.interest_coverage(),
    ])
    value = avg([
        ctx.p("trailing_pe", invert=True, positive_only=True),
        ctx.p("forward_pe", invert=True, positive_only=True),
        ctx.p("enterprise_to_ebitda", invert=True, positive_only=True),
    ])
    growth = ctx.growth()
    stability = ctx.stability()
    score = weighted([
        (quality, .20), (cashflow, .22), (balance, .18), (value, .20),
        (growth, .10), (stability, .10),
    ])
    return score, {
        "Energy Quality": quality, "Cash Flow": cashflow, "Balance": balance,
        "Valuation": value, "Growth": growth, "Stability": stability,
    }


def biotech_shadow(ctx):
    def runway(x):
        cash = n(x.get("net_cash"))
        fcf = n(x.get("free_cash_flow"))
        # net_cash is a conservative substitute for unavailable total_cash in
        # the published row; positive FCF keeps the production 100-point rule.
        if fcf is not None and fcf >= 0:
            return None
        return cash / abs(fcf) if cash is not None and cash > 0 and fcf is not None and fcf < 0 else None

    fcf = n(ctx.row.get("free_cash_flow"))
    if fcf is not None and fcf >= 0:
        runway_score = 100.0
    else:
        runway_score = ctx.derived("cash_runway_proxy", runway)

    net_cash = ctx.net_cash_to_cap()
    dilution = ctx.p("diluted_shares_yoy", invert=True)
    quality = avg([ctx.p("gross_margin"), ctx.p("roa")])
    growth = ctx.growth()
    stability = ctx.stability()
    score = weighted([
        (runway_score, .25), (net_cash, .15), (dilution, .20),
        (growth, .20), (quality, .10), (stability, .10),
    ])
    return score, {
        "Cash Runway": runway_score, "Net Cash": net_cash,
        "Dilution Discipline": dilution, "Growth": growth,
        "Operating Quality": quality, "Stability": stability,
    }


def growth_tech_shadow(ctx):
    quality = ctx.quality()
    growth = ctx.growth()
    balance = ctx.balance()
    cashflow = ctx.cashflow()
    execution = avg([
        ctx.p("revenue_yoy_acceleration_pp"),
        ctx.p("net_margin_yoy_change_pp"),
        ctx.p("eps_yoy_acceleration_pp"),
    ])
    earnings_quality = avg([
        ctx.p("cash_conversion_ratio"),
        ctx.p("accrual_ratio", invert=True),
        ctx.p("fcf_margin"),
    ])
    capital_allocation = avg([
        ctx.p("diluted_shares_yoy", invert=True),
        ctx.p("roce_proxy"),
    ])
    value = avg([
        ctx.p("forward_pe", invert=True, positive_only=True),
        ctx.value(
            "fcf_yield",
            plausible_fcf_yield(ctx.row),
            [plausible_fcf_yield(x) for x in ctx.peers],
            [plausible_fcf_yield(x) for x in ctx.all_rows],
            invert=True,
        ),
    ])
    stability = ctx.stability()
    score = weighted([
        (quality, .20), (growth, .22), (balance, .12), (cashflow, .10),
        (value, .07), (execution, .12), (earnings_quality, .09),
        (capital_allocation, .05), (stability, .03),
    ])
    return score, {
        "Quality": quality, "Growth": growth, "Balance": balance,
        "Cash Flow": cashflow, "Valuation": value, "Execution": execution,
        "Earnings Quality": earnings_quality,
        "Capital Allocation": capital_allocation, "Stability": stability,
    }


MODEL_BUILDERS = {
    "bank": bank_shadow,
    "reit": reit_shadow,
    "insurance": insurance_shadow,
    "utility": utility_shadow,
    "energy": energy_shadow,
    "biotech": biotech_shadow,
    "growth_tech": growth_tech_shadow,
}


def rank_map(rows, field):
    ordered = sorted(
        ((str(r.get("ticker")), n(r.get(field))) for r in rows if n(r.get(field)) is not None),
        key=lambda x: x[1],
        reverse=True,
    )
    return {ticker: i + 1 for i, (ticker, _) in enumerate(ordered)}


def model_shadow(model, peers, equities):
    builder = MODEL_BUILDERS[model]
    out = []
    for row in peers:
        ctx = ShadowContext(row, peers, equities)
        candidate, dims = builder(ctx)
        candidate = apply_cap(candidate, row)
        if candidate is None:
            continue
        raw = raw_score(row)
        public = n(row.get("score"))
        out.append({
            "ticker": row.get("ticker"),
            "name": row.get("name"),
            "sector": row.get("sector"),
            "score_model": model,
            "production_score": public,
            "production_score_raw": raw,
            "peer_shadow_score": round(candidate, 2),
            "delta_vs_raw": round(candidate - raw, 2) if raw is not None else None,
            "delta_vs_published": round(candidate - public, 2) if public is not None else None,
            "score_cap": row.get("score_cap"),
            "shadow_dimensions": {
                key: round(value, 2) if value is not None else None
                for key, value in dims.items()
            },
            "benchmark_scopes": ctx.scopes,
        })

    prod_rank = rank_map(
        [{"ticker": x.get("ticker"), "_rank": x.get("production_score_raw")} for x in out],
        "_rank",
    )
    shadow_rank = rank_map(out, "peer_shadow_score")
    for item in out:
        ticker = str(item.get("ticker"))
        item["production_model_rank"] = prod_rank.get(ticker)
        item["shadow_model_rank"] = shadow_rank.get(ticker)
        if item["production_model_rank"] and item["shadow_model_rank"]:
            item["rank_shift"] = item["production_model_rank"] - item["shadow_model_rank"]
    return out


def summarize_model(model, peers, shadow_rows):
    deltas = [n(x.get("delta_vs_raw")) for x in shadow_rows]
    deltas = [x for x in deltas if x is not None]
    scope_counts = defaultdict(int)
    for item in shadow_rows:
        for meta in item.get("benchmark_scopes") or []:
            scope_counts[str(meta.get("scope") or "unknown")] += 1
    return {
        "score_model": model,
        "peer_rows": len(peers),
        "shadow_rows": len(shadow_rows),
        "mean_delta_vs_raw": round(sum(deltas) / len(deltas), 3) if deltas else None,
        "mean_absolute_delta_vs_raw": round(sum(abs(x) for x in deltas) / len(deltas), 3) if deltas else None,
        "max_absolute_delta_vs_raw": round(max((abs(x) for x in deltas), default=0), 3),
        "benchmark_scope_counts": dict(sorted(scope_counts.items())),
        "largest_score_shifts": sorted(
            shadow_rows, key=lambda x: abs(n(x.get("delta_vs_raw")) or 0), reverse=True
        )[:10],
        "largest_rank_shifts": sorted(
            shadow_rows, key=lambda x: abs(n(x.get("rank_shift")) or 0), reverse=True
        )[:10],
    }


def build_shadow(rows):
    equities = [
        r for r in rows
        if isinstance(r, dict)
        and str(r.get("quote_type") or "").upper() not in {"ETF", "CRYPTO", "FUND", "MUTUALFUND"}
        and str(r.get("pipeline_status") or "") not in {"equity_catalog_only", "equity_carried_forward"}
        and raw_score(r) is not None
    ]
    by_model = defaultdict(list)
    for row in equities:
        model = str(row.get("score_model") or "general")
        if model in MODEL_BUILDERS:
            by_model[model].append(row)

    all_shadow = []
    summaries = {}
    for model in SPECIALIST_MODELS:
        peers = by_model.get(model, [])
        shadow_rows = model_shadow(model, peers, equities) if peers else []
        all_shadow.extend(shadow_rows)
        summaries[model] = summarize_model(model, peers, shadow_rows)

    return equities, all_shadow, summaries


def main():
    payload = json.loads(STOCKS.read_text(encoding="utf-8"))
    rows = [r for r in (payload.get("stocks") or []) if isinstance(r, dict)]
    equities, shadow_rows, summaries = build_shadow(rows)

    out = {
        "schema_version": 2,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "production_unchanged": True,
        "phase": "all_specialist_peer_normalization_shadow",
        "methodology": {
            "models": list(SPECIALIST_MODELS),
            "min_peer_observations": MIN_PEERS,
            "fallback": "global equity universe per metric when fewer than 20 finite same-model observations exist",
            "weights": "identical to the production specialist pack",
            "risk_caps": "existing production score_cap applied unchanged",
            "comparison_layer": "peer candidate compared with score_raw; public confidence moderation remains separate",
        },
        "equity_rows": len(equities),
        "shadow_rows": len(shadow_rows),
        "model_summaries": summaries,
        "rows": shadow_rows,
        "activation_rule": (
            "Shadow only. Do not activate peer-first production scoring until prospective "
            "28/84/168-day cohorts show stable improvement across multiple matured cohorts."
        ),
    }
    OUT.write_text(
        json.dumps(out, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        "Peer shadow v2: "
        + ", ".join(
            f"{model}={summary['shadow_rows']}/{summary['peer_rows']}"
            for model, summary in summaries.items()
        )
    )


if __name__ == "__main__":
    main()
