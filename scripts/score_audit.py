"""Empirical diagnostic audit for the Vestra composite score.

This module does NOT change production scores. It measures redundancy, sector
concentration and sensitivity to the actual weight pack used by each score model.
The audit reads full stocks.json because specialist models expose their native
components through score_dimensions; reconstructing every company with the general
weights would be methodologically wrong.
"""
from __future__ import annotations

import datetime as dt
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STOCKS = ROOT / "data" / "stocks.json"
OUT = ROOT / "data" / "score_audit.json"

MODEL_WEIGHTS = {
    "general": {
        "Quality": .18, "Growth": .15, "Balance": .14, "Cash Flow": .08,
        "Valuation": .12, "Execution": .10, "Earnings Quality": .10,
        "Capital Allocation": .08, "Stability": .05,
    },
    "growth_tech": {
        "Quality": .20, "Growth": .22, "Balance": .12, "Cash Flow": .10,
        "Valuation": .07, "Execution": .12, "Earnings Quality": .09,
        "Capital Allocation": .05, "Stability": .03,
    },
    "bank": {
        "Bank Quality": .22, "Efficiency": .13, "Asset Quality": .10,
        "Capital Proxy": .15, "Growth": .15, "Valuation": .15,
        "Income": .05, "Stability": .05,
    },
    "reit": {
        "REIT Quality": .22, "Growth": .16, "Leverage": .20,
        "P/FFO Value": .20, "Distribution": .17, "Stability": .05,
    },
    "insurance": {
        "Insurance Quality": .22, "Underwriting Proxy": .18,
        "Capital Proxy": .18, "Growth": .12, "Valuation": .17,
        "Income": .08, "Stability": .05,
    },
    "utility": {
        "Utility Quality": .18, "Balance": .22, "Income": .18,
        "Valuation": .17, "Growth": .10, "Stability": .10,
        "Cash Flow": .05,
    },
    "energy": {
        "Energy Quality": .20, "Cash Flow": .22, "Balance": .18,
        "Valuation": .20, "Growth": .10, "Stability": .10,
    },
    "biotech": {
        "Cash Runway": .25, "Net Cash": .15, "Dilution Discipline": .20,
        "Growth": .20, "Operating Quality": .10, "Stability": .10,
    },
}


def num(v):
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def mean(xs):
    vals = [x for x in xs if x is not None]
    return sum(vals) / len(vals) if vals else None


def pearson_pairs(pairs):
    vals = [(num(a), num(b)) for a, b in pairs]
    vals = [(a, b) for a, b in vals if a is not None and b is not None]
    if len(vals) < 8:
        return None
    ax = sum(a for a, _ in vals) / len(vals)
    bx = sum(b for _, b in vals) / len(vals)
    cov = sum((a - ax) * (b - bx) for a, b in vals)
    va = sum((a - ax) ** 2 for a, _ in vals)
    vb = sum((b - bx) ** 2 for _, b in vals)
    if va <= 0 or vb <= 0:
        return None
    return cov / math.sqrt(va * vb)


def rank(values):
    indexed = sorted(enumerate(values), key=lambda x: x[1])
    out = [0.0] * len(values)
    i = 0
    while i < len(indexed):
        j = i + 1
        while j < len(indexed) and indexed[j][1] == indexed[i][1]:
            j += 1
        avg_rank = (i + j - 1) / 2.0 + 1.0
        for k in range(i, j):
            out[indexed[k][0]] = avg_rank
        i = j
    return out


def spearman_pairs(pairs):
    vals = [(num(a), num(b)) for a, b in pairs]
    vals = [(a, b) for a, b in vals if a is not None and b is not None]
    if len(vals) < 8:
        return None
    return pearson_pairs(zip(rank([a for a, _ in vals]), rank([b for _, b in vals])))


def weighted_dimensions(dimensions, weights):
    parts = []
    for name, weight in weights.items():
        value = num((dimensions or {}).get(name))
        if value is not None:
            parts.append((value, weight))
    if not parts:
        return None
    total = sum(w for _, w in parts)
    return sum(v * w for v, w in parts) / total if total else None


def top_set(scored, frac=.10):
    valid = [(ticker, score) for ticker, score in scored if score is not None]
    valid.sort(key=lambda x: x[1], reverse=True)
    n = max(1, round(len(valid) * frac)) if valid else 0
    return {ticker for ticker, _ in valid[:n]}


def jaccard(a, b):
    return len(a & b) / len(a | b) if a or b else 1.0


def model_audit(model, rows):
    weights = MODEL_WEIGHTS.get(model)
    if not weights:
        return {"score_model": model, "n": len(rows), "status": "unknown_weight_pack"}

    dimension_coverage = {}
    for name in weights:
        present = sum(1 for r in rows if num((r.get("score_dimensions") or {}).get(name)) is not None)
        dimension_coverage[name] = {
            "present": present,
            "coverage_pct": round(100 * present / len(rows), 1) if rows else 0.0,
        }

    correlations = []
    names = list(weights)
    for i, left in enumerate(names):
        for right in names[i + 1:]:
            pairs = [((r.get("score_dimensions") or {}).get(left), (r.get("score_dimensions") or {}).get(right)) for r in rows]
            p = pearson_pairs(pairs); s = spearman_pairs(pairs)
            if p is not None or s is not None:
                correlations.append({
                    "left": left, "right": right,
                    "pearson": round(p, 3) if p is not None else None,
                    "spearman": round(s, 3) if s is not None else None,
                    "potential_redundancy": bool(s is not None and abs(s) >= .75),
                })
    correlations.sort(key=lambda x: abs(x.get("spearman") or 0), reverse=True)

    baseline = [(str(r.get("ticker")), weighted_dimensions(r.get("score_dimensions"), weights)) for r in rows]
    production_vs_reconstructed = spearman_pairs([(r.get("score"), dict(baseline).get(str(r.get("ticker")))) for r in rows])
    baseline_top = top_set(baseline)
    sensitivity = []
    for name in names:
        for multiplier in (.5, .8, 1.2, 1.5):
            altered = dict(weights); altered[name] *= multiplier
            alt = [(str(r.get("ticker")), weighted_dimensions(r.get("score_dimensions"), altered)) for r in rows]
            alt_map = dict(alt)
            rho = spearman_pairs([(score, alt_map.get(ticker)) for ticker, score in baseline])
            sensitivity.append({
                "dimension": name,
                "weight_multiplier": multiplier,
                "rank_spearman": round(rho, 4) if rho is not None else None,
                "top_decile_jaccard": round(jaccard(baseline_top, top_set(alt)), 4),
            })

    effective = Counter(
        sum(1 for name in names if num((r.get("score_dimensions") or {}).get(name)) is not None)
        for r in rows
    )
    return {
        "score_model": model,
        "n": len(rows),
        "weights": weights,
        "mean_production_score": round(mean([num(r.get("score")) for r in rows]) or 0, 2),
        "mean_data_coverage_pct": round(mean([num(r.get("data_coverage_pct")) for r in rows]) or 0, 2),
        "production_vs_reconstructed_rank_spearman": round(production_vs_reconstructed, 4) if production_vs_reconstructed is not None else None,
        "dimension_coverage": dimension_coverage,
        "effective_dimension_count_distribution": dict(sorted(effective.items())),
        "dimension_correlations": correlations,
        "weight_sensitivity": sensitivity,
        "redundant_pair_count": sum(1 for c in correlations if c["potential_redundancy"]),
        "material_sensitivity_count": sum(1 for x in sensitivity if (x.get("rank_spearman") or 1) < .95 or x["top_decile_jaccard"] < .75),
    }


def main():
    payload = json.loads(STOCKS.read_text(encoding="utf-8"))
    rows = [
        r for r in (payload.get("stocks") or [])
        if isinstance(r, dict)
        and str(r.get("quote_type") or "").upper() not in {"ETF", "CRYPTO", "FUND", "MUTUALFUND"}
        and num(r.get("score")) is not None
        and str(r.get("pipeline_status") or "") not in {"equity_catalog_only", "equity_carried_forward"}
    ]

    models = defaultdict(list)
    for r in rows:
        models[str(r.get("score_model") or "general")].append(r)
    model_results = [model_audit(model, model_rows) for model, model_rows in sorted(models.items(), key=lambda x: len(x[1]), reverse=True)]

    sector_counts = Counter(str(r.get("sector") or "Unknown") for r in rows)
    top_n = max(1, round(len(rows) * .10)) if rows else 0
    production_top = sorted(rows, key=lambda r: num(r.get("score")) or -1, reverse=True)[:top_n]
    top_sector_counts = Counter(str(r.get("sector") or "Unknown") for r in production_top)
    sector_bias = []
    for sector, total in sector_counts.most_common():
        top_count = top_sector_counts.get(sector, 0)
        universe_share = total / len(rows) if rows else 0
        top_share = top_count / top_n if top_n else 0
        sector_rows = [r for r in rows if str(r.get("sector") or "Unknown") == sector]
        sector_bias.append({
            "sector": sector,
            "universe_n": total,
            "top_decile_n": top_count,
            "universe_share_pct": round(universe_share * 100, 2),
            "top_decile_share_pct": round(top_share * 100, 2),
            "top_decile_representation_ratio": round(top_share / universe_share, 2) if universe_share else None,
            "mean_score": round(mean([num(r.get("score")) for r in sector_rows]) or 0, 2),
        })

    flags = []
    for model in model_results:
        if model.get("redundant_pair_count", 0):
            flags.append({"type": "dimension_redundancy", "score_model": model["score_model"], "severity": "review", "count": model["redundant_pair_count"]})
        if model.get("material_sensitivity_count", 0):
            flags.append({"type": "weight_sensitivity", "score_model": model["score_model"], "severity": "review", "count": model["material_sensitivity_count"]})
        rho = model.get("production_vs_reconstructed_rank_spearman")
        if rho is not None and rho < .98:
            flags.append({"type": "reconstruction_mismatch", "score_model": model["score_model"], "severity": "investigate", "rank_spearman": rho})
    skewed = [x for x in sector_bias if x["universe_n"] >= 20 and (x["top_decile_representation_ratio"] or 0) >= 2]
    if skewed:
        flags.append({"type": "sector_concentration", "severity": "review", "sectors": [x["sector"] for x in skewed]})

    out = {
        "schema_version": 2,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "rows_analysed": len(rows),
        "methodology": {
            "purpose": "diagnostic only; production score/weights are unchanged",
            "source": "full stocks.json score_dimensions, so each specialist model is tested with its real production weight pack",
            "weight_perturbations": [.5, .8, 1.2, 1.5],
            "redundancy_threshold": "absolute Spearman >= 0.75",
            "material_sensitivity": "rank Spearman < 0.95 or top-decile Jaccard < 0.75",
            "sector_bias_note": "descriptive concentration only; not causal evidence",
        },
        "model_audits": model_results,
        "sector_top_decile_bias": sector_bias,
        "flags": flags,
        "known_methodological_issue_to_test": "Several specialist packs still inherit globally-ranked base components such as growth, stability or interest coverage before model-specific weighting. Do not change this until prospective validation can compare global vs peer-normalized variants out of sample.",
        "next_step": "Combine cross-sectional stability with prospective 4/12/24-week rank IC and top-minus-bottom return spreads before changing production weights or normalization universes.",
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Score audit v2: {len(rows)} equities across {len(model_results)} score models; flags={len(flags)}")


if __name__ == "__main__":
    main()
