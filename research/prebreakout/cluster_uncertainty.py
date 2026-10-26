"""Issuer-clustered resampling for offline paired net-payoff differences.

Research only: uncertainty is conditional on observed issuer clusters and does
not replace chronological out-of-sample evaluation or address common date shocks.
"""
from __future__ import annotations
from collections import defaultdict
import math
import random
import statistics


def issuer_cluster_bootstrap(deltas: list[dict], *, repetitions: int = 2000,
                             seed: int = 1729, minimum_issuers: int = 30) -> dict:
    """Percentile 95% CI resampling entire issuer histories, not individual rows.

    Input: issuer_id, episode_id, signal_date, delta_net_pct on matched trades.
    Every row must be a unique real episode. Reject insufficient diversity.
    Does not calculate a p-value or assert alpha.
    """
    if type(repetitions) is not int or repetitions < 200:
        raise ValueError("at least 200 bootstrap replications required")
    if type(seed) is not int or type(minimum_issuers) is not int or minimum_issuers < 2:
        raise ValueError("invalid bootstrap parameters")
    grouped = defaultdict(list)
    seen = set()
    for row in deltas:
        if not isinstance(row, dict):
            raise ValueError("invalid row")
        issuer, episode, day = (row.get(k) for k in ("issuer_id", "episode_id", "signal_date"))
        key = (issuer, episode, day)
        if not all(isinstance(v, str) and v for v in key) or key in seen:
            raise ValueError("missing or repeated event identity")
        seen.add(key)
        value = row.get("delta_net_pct")
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError("invalid payoff delta")
        grouped[issuer].append(float(value))
    issuers = sorted(grouped)
    if len(issuers) < minimum_issuers:
        return {"status": "insufficient_clusters", "issuers": len(issuers),
                "episodes": len(seen), "mean_delta_net_pct": None,
                "ci95_lower_pct": None, "ci95_upper_pct": None}
    rng = random.Random(seed)
    means = []
    for _ in range(repetitions):
        sampled = [issuer for _ in issuers for issuer in [rng.choice(issuers)]]
        observations = [v for issuer in sampled for v in grouped[issuer]]
        means.append(statistics.mean(observations))
    means.sort()
    low = means[int(0.025 * (repetitions - 1))]
    high = means[int(0.975 * (repetitions - 1))]
    all_values = [v for issuer in issuers for v in grouped[issuer]]
    return {"status": "descriptive_issuer_cluster_interval_not_oos_proof",
            "issuers": len(issuers), "episodes": len(seen),
            "mean_delta_net_pct": round(statistics.mean(all_values), 6),
            "ci95_lower_pct": round(low, 6), "ci95_upper_pct": round(high, 6),
            "method": "issuer_cluster_percentile_bootstrap",
            "repetitions": repetitions,
            "limitations": "shared_date_shocks_selection_bias_and_temporal_dependence_not_resolved"}
