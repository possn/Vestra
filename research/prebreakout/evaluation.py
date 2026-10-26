"""Offline paired out-of-sample payoff analysis. No prediction or live ranking."""
from __future__ import annotations
from collections import defaultdict
import math
import statistics


def summarize_net_trades(trades: list[dict]) -> dict:
    """Require realized, net, nonduplicated episodes with declared execution costs.

    Each trade needs issuer_id, episode_id, signal_date, gross_return_pct and
    total_cost_pct; returns and costs must be finite. No imputed zero outcomes.
    """
    seen=set()
    net=[]
    issuers=set()
    for t in trades:
        key=(t["issuer_id"],t["episode_id"])
        if not all(isinstance(v,str) and v for v in key) or key in seen:
            raise ValueError("missing or duplicate episode identity")
        seen.add(key); issuers.add(t["issuer_id"])
        values=(t["gross_return_pct"],t["total_cost_pct"])
        if any(type(v) not in (float,int) or not math.isfinite(v) for v in values):
            raise ValueError("missing or nonfinite return/cost")
        if values[1]<0:
            raise ValueError("negative execution cost")
        net.append(values[0]-values[1])
    if not net:
        return {"status":"insufficient_evidence","n":0,"mean_net_pct":None,
                "median_net_pct":None,"profit_factor":None}
    wins=sum(v for v in net if v>0)
    losses=-sum(v for v in net if v<0)
    return {"status":"descriptive_only_not_validated",
            "n":len(net),"unique_issuers":len(issuers),
            "mean_net_pct":round(statistics.mean(net),6),
            "median_net_pct":round(statistics.median(net),6),
            "positive_fraction":round(sum(v>0 for v in net)/len(net),6),
            "profit_factor":round(wins/losses,6) if losses>0 else None,
            "profit_factor_status":"defined" if losses>0 else "undefined_no_losses",
            "net_returns_pct":net}


def paired_baseline_delta(challenger:list[dict], baseline:list[dict]) -> dict:
    """Same issuer/episode/date pairs only. Does not imply statistical significance."""
    def keyed(rows):
        mapped={}
        for row in rows:
            key=(row["issuer_id"],row["episode_id"],row["signal_date"])
            if key in mapped:
                raise ValueError("duplicate paired key")
            mapped[key]=row
        return mapped
    a=keyed(challenger);b=keyed(baseline)
    if set(a)!=set(b):
        raise ValueError("unmatched baseline episodes")
    if not a:
        return {"n":0,"mean_delta_net_pct":None,"status":"insufficient_evidence"}
    def net(row):
        x=row["gross_return_pct"];c=row["total_cost_pct"]
        if any(type(v) not in (int,float) or not math.isfinite(v) for v in (x,c)) or c<0:
            raise ValueError("invalid paired return/cost")
        return x-c
    delta=[net(a[k])-net(b[k]) for k in sorted(a)]
    return {"n":len(delta),"mean_delta_net_pct":round(statistics.mean(delta),6),
            "median_delta_net_pct":round(statistics.median(delta),6),
            "status":"descriptive_only_requires_clustered_uncertainty_and_oos",
            "delta_net_pct":delta}
