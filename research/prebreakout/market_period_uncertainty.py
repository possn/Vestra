"""Descriptive market-period block bootstrap for offline paired net returns.

Entire contiguous market periods are resampled together, preserving simultaneous
issuer shocks inside each period. This is NOT a two-way cluster confidence interval
and does NOT account for dependence across blocks or overlapping holding windows.
"""
from collections import defaultdict
from datetime import date
import math
import random
import statistics


def market_period_bootstrap(rows, *, repetitions=2000, seed=1729,
                            minimum_periods=12, minimum_issuers=30):
    """Require explicit predeclared period_id, e.g. YYYY-MM market months.

    Strictly reject repeated issuer episodes, unverified period identifiers and
    malformed deltas. One block contains ALL observations from that period.
    """
    if (type(repetitions) is not int or repetitions < 200 or
            type(minimum_periods) is not int or minimum_periods < 2 or
            type(minimum_issuers) is not int or minimum_issuers < 2 or
            type(seed) is not int):
        raise ValueError("invalid bootstrap settings")
    periods=defaultdict(list)
    seen=set()
    issuers=set()
    for row in rows:
        if not isinstance(row,dict):
            raise ValueError("invalid observation")
        issuer,episode,day,period=(row.get(k) for k in
                                 ("issuer_id","episode_id","signal_date","period_id"))
        if not all(isinstance(v,str) and v for v in (issuer,episode,day,period)):
            raise ValueError("missing event or period")
        try:
            signal=date.fromisoformat(day)
            if period!=signal.strftime("%Y-%m"):
                raise ValueError("period/date mismatch")
        except (ValueError,TypeError) as exc:
            raise ValueError("invalid market period") from exc
        identity=(issuer,episode)
        if identity in seen:
            raise ValueError("repeated episode")
        seen.add(identity)
        value=row.get("delta_net_pct")
        if type(value) not in (int,float) or not math.isfinite(value):
            raise ValueError("missing or nonfinite return")
        issuers.add(issuer)
        periods[period].append(float(value))
    keys=sorted(periods)
    if len(keys)<minimum_periods or len(issuers)<minimum_issuers:
        return {"status":"insufficient_periods_or_issuers","periods":len(keys),
                "issuers":len(issuers),"episodes":len(seen),
                "mean_delta_net_pct":None,"ci95_lower_pct":None,"ci95_upper_pct":None}
    rng=random.Random(seed)
    estimates=[]
    for _ in range(repetitions):
        draws=[rng.choice(keys) for _ in keys]
        values=[value for key in draws for value in periods[key]]
        estimates.append(statistics.mean(values))
    estimates.sort()
    values=[value for key in keys for value in periods[key]]
    return {"status":"descriptive_market_period_interval_not_oos_proof",
            "method":"market_month_block_percentile_bootstrap",
            "periods":len(keys),"issuers":len(issuers),"episodes":len(seen),
            "mean_delta_net_pct":round(statistics.mean(values),6),
            "ci95_lower_pct":round(estimates[int(.025*(repetitions-1))],6),
            "ci95_upper_pct":round(estimates[int(.975*(repetitions-1))],6),
            "limitations":"serial_dependence_cross_period_episodes_and_selection_bias_not_resolved"}
