"""Research-only audit report composing predeclared folds with paired net returns.

No prediction or live ranking. Reports are descriptive even if a bootstrap
interval excludes zero: temporal and shared-date dependencies remain.
"""
from __future__ import annotations
import hashlib
import json
from evaluation import summarize_net_trades, paired_baseline_delta
from cluster_uncertainty import issuer_cluster_bootstrap
from market_period_uncertainty import market_period_bootstrap
from walk_forward import walk_forward_folds


def evaluate_folds(events, challenger, baseline, boundaries, *,
                   dataset_sha256, embargo_sessions=20,
                   min_train_issuers=30, min_test_issuers=15,
                   bootstrap_issuers=30, repetitions=2000, seed=1729,
                   bootstrap_periods=12):
    """Require one matched, realized challenger/baseline payoff per event.

    Every fold is evaluated strictly from its test indices. Empty or
    insufficient folds expose null outcomes; synthetic tests are not alpha.
    """
    if not isinstance(dataset_sha256, str) or len(dataset_sha256)!=64:
        raise ValueError("missing immutable dataset checksum")
    try:
        int(dataset_sha256,16)
    except ValueError as exc:
        raise ValueError("invalid dataset checksum") from exc
    if len(events)!=len(challenger) or len(events)!=len(baseline):
        raise ValueError("incomplete matched event coverage")
    identities=set()
    for event,a,b in zip(events,challenger,baseline):
        key=(event["issuer_id"],event["episode_id"],event["signal_date"])
        if key in identities:
            raise ValueError("repeated event")
        identities.add(key)
        for record in (a,b):
            if (record["issuer_id"],record["episode_id"],record["signal_date"])!=key:
                raise ValueError("event/payoff misalignment")
    folds=walk_forward_folds(events,boundaries,embargo_sessions=embargo_sessions,
                             min_train_issuers=min_train_issuers,
                             min_test_issuers=min_test_issuers)
    reports=[]
    for fold in folds:
        report={"start_date":fold["start_date"],"end_date":fold["end_date"],
                "train_issuers":fold["train_issuers"],"test_issuers":fold["test_issuers"],
                "test_episodes":len(fold["test_indices"]),"status":fold["status"],
                "challenger":None,"baseline":None,"paired_delta":None,
                "issuer_interval":None,"market_period_interval":None}
        if fold["status"]=="eligible_for_offline_evaluation":
            subset_a=[challenger[i] for i in fold["test_indices"]]
            subset_b=[baseline[i] for i in fold["test_indices"]]
            result=paired_baseline_delta(subset_a,subset_b)
            differences=[{"issuer_id":a["issuer_id"],"episode_id":a["episode_id"],
                          "signal_date":a["signal_date"],"delta_net_pct":delta}
                         for a,delta in zip(sorted(subset_a,key=lambda t:(t["issuer_id"],t["episode_id"],t["signal_date"])),result["delta_net_pct"])]
            report.update(challenger=summarize_net_trades(subset_a),
                          baseline=summarize_net_trades(subset_b),
                          paired_delta=result,
                          issuer_interval=issuer_cluster_bootstrap(
                              differences,repetitions=repetitions,seed=seed,
                              minimum_issuers=bootstrap_issuers),
                          market_period_interval=market_period_bootstrap(
                              [dict(row,period_id=row["signal_date"][:7]) for row in differences],
                              repetitions=repetitions,seed=seed,
                              minimum_issuers=bootstrap_issuers,
                              minimum_periods=bootstrap_periods))
        reports.append(report)
    return {"schema_version":1,"research_only":True,"dataset_sha256":dataset_sha256,
            "status":"descriptive_folds_not_predictive_validation",
            "folds":reports,
            "limitations":["requires_independently_verified_point_in_time_dataset",
                           "issuer_bootstrap_does_not_handle_common_market_date_shocks",
                           "market_month_bootstrap_does_not_resolve_cross_month_dependence",
                           "fold_eligibility_does_not_prove_data_provenance",
                           "no_automatic_live_signal_or_probability_promotion"]}


def canonical_report_json(result):
    return json.dumps(result,sort_keys=True,ensure_ascii=False,allow_nan=False,
                      separators=(",",":"))+"\n"
