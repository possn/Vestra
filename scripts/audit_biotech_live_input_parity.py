"""On-demand validation against the exact pre-score RawMetrics cohort.

Call in the same pipeline execution immediately after score_universe(raw).
Never writes snapshots, changes scores, or alters risk decisions.
"""
from score import _score_model_for, _benchmark_values, _percentile_rank, _avg


def measure(raw, scored):
    equities = [r for r in raw if r.quote_type not in ("ETF", "CRYPTO")
                and r.error is None]
    peers = [r for r in equities if _score_model_for(r) == "biotech"]
    scored_by_ticker = {r.ticker: r for r in scored}
    def benchmark(field):
        values = [getattr(r, field) for r in peers]
        universal = [getattr(r, field) for r in equities]
        return _benchmark_values(values, universal)
    gross_ref, roa_ref = benchmark("gross_margin"), benchmark("roa")
    diffs = []
    for r in peers:
        published = (getattr(scored_by_ticker.get(r.ticker), "score_dimensions", None) or {}).get("Operating Quality")
        gross = _percentile_rank(r.gross_margin, gross_ref)
        roa = _percentile_rank(r.roa, roa_ref)
        native = _avg([gross, roa])
        if native is None or published is None:
            continue
        # ScoredTicker.score_dimensions is rounded to one decimal by score.py.
        diffs.append(abs(round(native, 1) - published))
    return {
        "biotech_input_rows": len(peers),
        "comparable_rows": len(diffs),
        "mean_absolute_parity_delta": sum(diffs)/len(diffs) if diffs else None,
        "max_absolute_parity_delta": max(diffs) if diffs else None,
        "outside_rounding_tolerance": sum(x>0.001 for x in diffs),
        "published_decimal_places": 1,
        "candidate_is_production": False,
    }



def _spearman(pairs):
    """Tie-aware Spearman on pairwise-observed scores; never fabricate missing data."""
    if len(pairs) < 3:
        return None

    def ranks(items):
        ordered = sorted(range(len(items)), key=lambda i: items[i])
        out = [0.0] * len(items)
        pos = 0
        while pos < len(ordered):
            end = pos + 1
            while end < len(ordered) and items[ordered[end]] == items[ordered[pos]]:
                end += 1
            midrank = ((pos + 1) + end) / 2
            for k in range(pos, end):
                out[ordered[k]] = midrank
            pos = end
        return out

    xs, ys = zip(*pairs)
    a, b = ranks(xs), ranks(ys)
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    va = sum((x - ma) ** 2 for x in a)
    vb = sum((y - mb) ** 2 for y in b)
    if not va or not vb:
        return None
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (va * vb) ** 0.5


def shadow_ablation(raw, scored):
    """Same-run sensitivity only. No mutation of Score or investment decisions.

    This is NOT the published 165-company historical cohort. Score-shift is
    the unconstrained composite contribution (10% dimension weight), not
    a new production Score after caps / risk gates.
    """
    equities = [r for r in raw if r.quote_type not in ("ETF", "CRYPTO") and r.error is None]
    peers = [r for r in equities if _score_model_for(r) == "biotech"]
    scored_by_ticker = {r.ticker: r for r in scored}
    def reference(attr):
        return _benchmark_values([getattr(r, attr) for r in peers],
                                 [getattr(r, attr) for r in equities])
    gross_ref, roa_ref = reference("gross_margin"), reference("roa")
    observations = []
    for r in peers:
        score_row = scored_by_ticker.get(r.ticker)
        dims = (getattr(score_row, "score_dimensions", None) or {})
        original = dims.get("Operating Quality")
        runway = dims.get("Cash Runway")
        gross = _percentile_rank(r.gross_margin, gross_ref)
        roa = _percentile_rank(r.roa, roa_ref)
        observations.append((original, runway, gross, roa, getattr(score_row, "score_raw", None)))
    candidates = []
    for weight in (0.0, 0.1, 0.2, 0.3, 0.4, 0.5):
        pairs = []
        composite_changes = []
        ranking_rows = []
        for original, runway, gross, roa, score_raw in observations:
            # A missing input must not silently be reweighted into a full-confidence
            # alternative: preserve production's mean-available semantics.
            values = [(gross, 1 - weight), (roa, weight)]
            available = [(v, w) for v, w in values if v is not None and w > 0]
            denom = sum(w for _, w in available)
            candidate = sum(v * w for v, w in available) / denom if denom else None
            if runway is not None and candidate is not None:
                pairs.append((runway, candidate))
            if original is not None and candidate is not None:
                composite_changes.append(abs(candidate - original) * 0.10)
                if score_raw is not None:
                    ranking_rows.append((float(score_raw), float(score_raw) + 0.10 * (candidate - original)))
        # Pairwise rank displacement within the same-run Biotech cohort only.
        def positions(values):
            order = sorted(range(len(values)), key=lambda i: (-values[i], i))
            return {idx: rank for rank, idx in enumerate(order, 1)}
        base = positions([x for x, _ in ranking_rows])
        alternate = positions([y for _, y in ranking_rows])
        displacement = [abs(base[i] - alternate[i]) for i in base]
        candidates.append({
            "roa_weight": weight,
            "pairs": len(pairs),
            "runway_quality_spearman": round(_spearman(pairs), 4) if _spearman(pairs) is not None else None,
            "mean_abs_uncapped_composite_shift": round(sum(composite_changes) / len(composite_changes), 4) if composite_changes else None,
            "uncapped_ranking_rows": len(ranking_rows),
            "uncapped_rank_shifts_ge_10": sum(d >= 10 for d in displacement) if displacement else None,
            "uncapped_max_rank_shift": max(displacement) if displacement else None,
        })
    return {"same_run_biotech_rows": len(peers), "historical_cohort_comparable": False,
            "candidates": candidates}
