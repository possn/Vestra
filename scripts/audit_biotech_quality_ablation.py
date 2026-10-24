"""Read-only biotech quality ablation against the canonical published snapshot."""
import json
import math
from pathlib import Path

import score_audit
import score_peer_shadow

ROOT = Path(__file__).resolve().parents[1]


def _percentile(v, pool):
    try:
        v = float(v)
        clean = [float(x) for x in pool if x is not None and math.isfinite(float(x))]
    except (TypeError, ValueError):
        return None
    if not clean or not math.isfinite(v):
        return None
    return 100.0 * sum(x <= v for x in clean) / len(clean)


def report(path=ROOT / "data/stocks.json"):
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    stocks = [x for x in payload.get("stocks", []) if isinstance(x, dict)]
    _, shadow, _ = score_peer_shadow.build_shadow(stocks)
    biotech = [x for x in shadow if x.get("score_model") == "biotech"]
    raw = {str(row.get("ticker")): row for row in stocks}
    reference_gross = [raw.get(str(x.get("ticker")), {}).get("gross_margin") for x in biotech]
    pairs = []
    for item in biotech:
        dims = item.get("shadow_dimensions") or {}
        runway = score_peer_shadow.n(dims.get("Cash Runway"))
        original = score_peer_shadow.n(dims.get("Operating Quality"))
        gross = raw.get(str(item.get("ticker")), {}).get("gross_margin")
        candidate = _percentile(gross, reference_gross)
        if None not in (runway, original, candidate):
            pairs.append((runway, original, candidate))
    # Ablation sweep: recombine peer-percentile gross margin and ROA, leaving
    # Cash Runway and every other specialist score pillar unchanged.
    # Production score uses peer_attr_values with a global-universe fallback
    # when fewer than 20 observations exist. The published stocks snapshot may
    # not reproduce the exact pre-publish RawMetrics cohort; compare both
    # benchmarks and report their uncertainty explicitly.
    all_equities = [row for row in stocks if row.get("quote_type") not in ("ETF", "CRYPTO") and not row.get("error")]
    all_gross = [row.get("gross_margin") for row in all_equities]
    all_roa = [row.get("roa") for row in all_equities]
    peer_gross_count = sum(x is not None for x in reference_gross)
    gross_benchmark = reference_gross if peer_gross_count >= 20 else all_gross
    reference_roa = [raw.get(str(x.get("ticker")), {}).get("roa") for x in biotech]
    peer_roa_count = sum(x is not None for x in reference_roa)
    roa_benchmark = reference_roa if peer_roa_count >= 20 else all_roa
    weights = (0.0, 0.1, 0.2, 0.3, 0.4, 0.5)
    sweep = []
    for roa_weight in weights:
        rows_at_weight = []
        for item in biotech:
            dims = item.get("shadow_dimensions") or {}
            runway = score_peer_shadow.n(dims.get("Cash Runway"))
            old_quality = score_peer_shadow.n(dims.get("Operating Quality"))
            old_score = score_peer_shadow.n(item.get("peer_shadow_score"))
            source = raw.get(str(item.get("ticker")), {})
            gross = _percentile(source.get("gross_margin"), reference_gross)
            roa = _percentile(source.get("roa"), reference_roa)
            if None in (runway, old_quality, old_score) or (gross is None and roa is None):
                continue
            components = [(gross, 1-roa_weight), (roa, roa_weight)]
            available = [(v,w) for v,w in components if v is not None and w > 0]
            candidate = sum(v*w for v,w in available) / sum(w for _,w in available)
            rows_at_weight.append((str(item.get("ticker")), runway, old_quality, old_score,
                                   candidate, old_score + .10*(candidate-old_quality)))
        def ranks(index):
            return {x[0]: i for i,x in enumerate(sorted(rows_at_weight,key=lambda x:(-x[index],x[0])),1)}
        old_ranks, new_ranks = ranks(3), ranks(5)
        shift = [abs(new_ranks[x[0]]-old_ranks[x[0]]) for x in rows_at_weight]
        delta = [abs(x[5]-x[3]) for x in rows_at_weight]
        sweep.append({
            "roa_weight": roa_weight, "rows": len(rows_at_weight),
            "runway_quality_rho": score_audit.spearman_pairs([(x[1],x[4]) for x in rows_at_weight]),
            "mean_abs_composite_shift": sum(delta)/len(delta) if delta else None,
            "max_abs_composite_shift": max(delta) if delta else None,
            "rank_changes_ge_10": sum(s>=10 for s in shift),
            "max_abs_rank_shift": max(shift) if shift else None,
        })
    # The published dimensions are rounded to two decimals; validate the 50/50
    # candidate against native peer-percentile averaging before interpreting ranks.
    native_half = []
    benchmark_half = []
    native_diffs = []
    for item in biotech:
        source = raw.get(str(item.get("ticker")), {})
        dims = item.get("shadow_dimensions") or {}
        published = score_peer_shadow.n(dims.get("Operating Quality"))
        gross = _percentile(source.get("gross_margin"), reference_gross)
        roa = _percentile(source.get("roa"), reference_roa)
        available = [x for x in (gross, roa) if x is not None]
        bm_gross = _percentile(source.get("gross_margin"), gross_benchmark)
        bm_roa = _percentile(source.get("roa"), roa_benchmark)
        bm_available = [x for x in (bm_gross, bm_roa) if x is not None]
        if published is not None and bm_available:
            benchmark_half.append(abs(published - sum(bm_available)/len(bm_available)))
        if published is not None and available:
            delta = abs(published-sum(available)/len(available))
            native_half.append(delta)
            native_diffs.append((str(item.get("ticker")), round(delta,3), round(published,3)))
    def rho(a, b):
        return score_audit.spearman_pairs([(p[a], p[b]) for p in pairs])

    # The specialist composite gives Operating Quality a 10% weight. Keep all
    # other pillars fixed and measure the resulting ranking perturbation.
    scored = []
    for item in biotech:
        dims = item.get("shadow_dimensions") or {}
        old_quality = score_peer_shadow.n(dims.get("Operating Quality"))
        gross = raw.get(str(item.get("ticker")), {}).get("gross_margin")
        new_quality = _percentile(gross, reference_gross)
        old_score = score_peer_shadow.n(item.get("peer_shadow_score"))
        if None in (old_quality, new_quality, old_score):
            continue
        new_score = old_score + 0.10 * (new_quality - old_quality)
        scored.append((str(item.get("ticker")), old_score, new_score))
    old_rank = {x[0]: i for i, x in enumerate(sorted(scored, key=lambda x: (-x[1], x[0])), 1)}
    new_rank = {x[0]: i for i, x in enumerate(sorted(scored, key=lambda x: (-x[2], x[0])), 1)}
    changes = sorted(
        [(name, round(new-old, 3), new_rank[name]-old_rank[name])
         for name, old, new in scored],
        key=lambda x: abs(x[2]), reverse=True
    )
    shifts = [abs(x[2]-x[1]) for x in scored]
    return {
        "model": "biotech", "snapshot_rows": len(biotech), "comparable_pairs": len(pairs),
        "roa_weight_sweep": sweep,
        "benchmark_observations": {"biotech_gross": peer_gross_count, "biotech_roa": peer_roa_count, "all_equity_gross": sum(x is not None for x in all_gross), "all_equity_roa": sum(x is not None for x in all_roa)},
        "production_benchmark_50pct_parity": {"rows": len(benchmark_half), "mean_absolute_delta": sum(benchmark_half)/len(benchmark_half) if benchmark_half else None, "max_absolute_delta": max(benchmark_half) if benchmark_half else None},
        "native_50pct_parity": {"rows": len(native_half), "mean_absolute_delta": sum(native_half)/len(native_half) if native_half else None, "max_absolute_delta": max(native_half) if native_half else None, "outside_rounding_tolerance": sum(x>0.02 for x in native_half), "largest_discrepancies": sorted(native_diffs,key=lambda x:-x[1])[:10]},
        "production_quality_rho": rho(0, 1), "gross_only_candidate_rho": rho(0, 2),
        "mean_quality_shift": (sum(abs(x[2]-x[1]) for x in pairs)/len(pairs)) if pairs else None,
        "score_comparable_rows": len(scored),
        "mean_abs_composite_shift": sum(shifts)/len(shifts) if shifts else None,
        "max_abs_composite_shift": max(shifts) if shifts else None,
        "rank_changes_ge_10": sum(abs(c[2]) >= 10 for c in changes),
        "largest_rank_changes": changes[:10],
        "candidate_published": False,
    }


if __name__ == "__main__":
    print("BIOTECH_GROSS_ONLY_SHADOW " + json.dumps(report(), sort_keys=True))
