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
