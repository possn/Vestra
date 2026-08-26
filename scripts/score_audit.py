"""Empirical diagnostic audit for the Vestra composite score.

This module does NOT change the production score. It measures whether the current
cross-sectional dimensions are redundant, sector-biased or excessively sensitive
to the manually chosen weight vector. The output is a reproducible diagnostic in
data/score_audit.json so weight changes can be evidence-led rather than aesthetic.
"""
from __future__ import annotations

import datetime as dt
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "data" / "stocks-index.json"
OUT = ROOT / "data" / "score_audit.json"

DIMENSIONS = {
    "quality_pct": 18.0,
    "growth_pct": 15.0,
    "balance_pct": 14.0,
    "cashflow_pct": 8.0,
    "value_pct": 12.0,
    "execution_pct": 10.0,
    "earnings_quality_pct": 10.0,
    "capital_allocation_pct": 8.0,
    "stability_pct": 5.0,
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
    ra = rank([a for a, _ in vals])
    rb = rank([b for _, b in vals])
    return pearson_pairs(zip(ra, rb))


def weighted_score(row, weights):
    parts = []
    for field, weight in weights.items():
        value = num(row.get(field))
        if value is not None:
            parts.append((value, weight))
    if not parts:
        return None
    total = sum(w for _, w in parts)
    return sum(v * w for v, w in parts) / total if total else None


def top_set(scored, frac=0.10):
    valid = [(ticker, score) for ticker, score in scored if score is not None]
    valid.sort(key=lambda x: x[1], reverse=True)
    n = max(1, round(len(valid) * frac))
    return {ticker for ticker, _ in valid[:n]}


def overlap(a, b):
    return len(a & b) / len(a | b) if a or b else 1.0


def main():
    payload = json.loads(INDEX.read_text(encoding="utf-8"))
    rows = [
        r for r in (payload.get("stocks") or [])
        if isinstance(r, dict)
        and str(r.get("quote_type") or "").upper() not in {"ETF", "CRYPTO", "FUND", "MUTUALFUND"}
        and num(r.get("score")) is not None
        and str(r.get("pipeline_status") or "") not in {"equity_catalog_only", "equity_carried_forward"}
    ]

    coverage = {}
    for field in DIMENSIONS:
        present = sum(1 for r in rows if num(r.get(field)) is not None)
        coverage[field] = {
            "present": present,
            "coverage_pct": round(100 * present / len(rows), 1) if rows else 0.0,
        }

    correlations = []
    fields = list(DIMENSIONS)
    for i, left in enumerate(fields):
        for right in fields[i + 1:]:
            pairs = [(r.get(left), r.get(right)) for r in rows]
            p = pearson_pairs(pairs)
            s = spearman_pairs(pairs)
            if p is not None or s is not None:
                correlations.append({
                    "left": left,
                    "right": right,
                    "pearson": round(p, 3) if p is not None else None,
                    "spearman": round(s, 3) if s is not None else None,
                    "potential_redundancy": bool(s is not None and abs(s) >= 0.75),
                })
    correlations.sort(key=lambda x: abs(x.get("spearman") or 0), reverse=True)

    baseline = [(str(r.get("ticker")), weighted_score(r, DIMENSIONS)) for r in rows]
    baseline_top = top_set(baseline)
    sensitivity = []
    for field in fields:
        for multiplier in (0.5, 0.8, 1.2, 1.5):
            weights = dict(DIMENSIONS)
            weights[field] *= multiplier
            alt = [(str(r.get("ticker")), weighted_score(r, weights)) for r in rows]
            by_alt = dict(alt)
            rank_corr = spearman_pairs([(score, by_alt.get(ticker)) for ticker, score in baseline])
            sensitivity.append({
                "dimension": field,
                "weight_multiplier": multiplier,
                "rank_spearman": round(rank_corr, 4) if rank_corr is not None else None,
                "top_decile_jaccard": round(overlap(baseline_top, top_set(alt)), 4),
            })

    sector_counts = Counter(str(r.get("sector") or "Unknown") for r in rows)
    production_top_n = max(1, round(len(rows) * 0.10))
    production_top = sorted(rows, key=lambda r: num(r.get("score")) or -1, reverse=True)[:production_top_n]
    top_sector_counts = Counter(str(r.get("sector") or "Unknown") for r in production_top)
    sector_bias = []
    for sector, total in sector_counts.most_common():
        top_count = top_sector_counts.get(sector, 0)
        universe_share = total / len(rows) if rows else 0
        top_share = top_count / production_top_n if production_top_n else 0
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

    models = defaultdict(list)
    for r in rows:
        models[str(r.get("score_model") or "general")].append(r)
    model_summary = []
    for model, model_rows in sorted(models.items(), key=lambda x: len(x[1]), reverse=True):
        model_summary.append({
            "score_model": model,
            "n": len(model_rows),
            "mean_score": round(mean([num(r.get("score")) for r in model_rows]) or 0, 2),
            "mean_data_coverage_pct": round(mean([num(r.get("data_coverage_pct")) for r in model_rows]) or 0, 2),
            "dimension_means": {
                f: round(mean([num(r.get(f)) for r in model_rows]) or 0, 2)
                for f in fields
            },
        })

    effective_dimension_count = Counter(
        sum(1 for field in fields if num(r.get(field)) is not None)
        for r in rows
    )

    flags = []
    redundant = [c for c in correlations if c["potential_redundancy"]]
    if redundant:
        flags.append({
            "type": "dimension_redundancy",
            "severity": "review",
            "detail": f"{len(redundant)} dimension pairs have |Spearman| >= 0.75",
        })
    unstable = [x for x in sensitivity if (x.get("rank_spearman") or 1) < 0.95 or x["top_decile_jaccard"] < 0.75]
    if unstable:
        flags.append({
            "type": "weight_sensitivity",
            "severity": "review",
            "detail": f"{len(unstable)} weight perturbations materially change rank/top-decile membership",
        })
    skewed = [x for x in sector_bias if x["universe_n"] >= 20 and (x["top_decile_representation_ratio"] or 0) >= 2.0]
    if skewed:
        flags.append({
            "type": "sector_concentration",
            "severity": "review",
            "detail": "Top-decile representation is >=2x universe share in: " + ", ".join(x["sector"] for x in skewed[:6]),
        })

    out = {
        "schema_version": 1,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "methodology": {
            "purpose": "diagnostic only; production weights are not changed",
            "baseline_weights": DIMENSIONS,
            "universe": "current refreshed equities with a production score; ETFs/crypto/carried rows excluded",
            "sensitivity": "each dimension weight independently multiplied by 0.5, 0.8, 1.2 and 1.5; missing dimensions re-normalize as production does",
            "redundancy_threshold": "absolute Spearman >= 0.75",
            "sector_bias_note": "descriptive concentration diagnostic, not evidence of causality",
        },
        "rows_analysed": len(rows),
        "dimension_coverage": coverage,
        "effective_dimension_count_distribution": dict(sorted(effective_dimension_count.items())),
        "dimension_correlations": correlations,
        "weight_sensitivity": sensitivity,
        "sector_top_decile_bias": sector_bias,
        "score_model_summary": model_summary,
        "flags": flags,
        "next_step": "Do not tune weights from this cross-section alone. Combine these diagnostics with prospective 4/12/24-week validation before production weight changes.",
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Score audit: {len(rows)} equities, {len(redundant)} redundant pairs, {len(unstable)} sensitive perturbations")


if __name__ == "__main__":
    main()
