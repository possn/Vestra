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
        diffs.append(abs(native - published))
    return {
        "biotech_input_rows": len(peers),
        "comparable_rows": len(diffs),
        "mean_absolute_parity_delta": sum(diffs)/len(diffs) if diffs else None,
        "max_absolute_parity_delta": max(diffs) if diffs else None,
        "outside_rounding_tolerance": sum(x>0.02 for x in diffs),
        "candidate_is_production": False,
    }
