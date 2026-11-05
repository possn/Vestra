"""Prospective, persistent validation of Vestra Opportunity rankings.

This tracker freezes the opportunity evidence genuinely known at each weekly
cohort and materialises realised returns only when 28/84/168-day horizons mature.
It is observational: it never changes production Opportunity weights or gates.

The aim is to answer whether higher-ranked, better-supported opportunities
actually deliver stronger and more consistent forward returns out of sample.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

try:
    from scripts.score_forward_validation import corporate_action_adjusted_return
except ModuleNotFoundError:
    from score_forward_validation import corporate_action_adjusted_return

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "data" / "stocks-index.json"
HISTORY = ROOT / "data" / "opportunity_validation_history.json"
REPORT = ROOT / "data" / "opportunity_validation_report.json"
HORIZONS = (28, 84, 168)
MAX_HORIZON_LATENESS_DAYS = 10
RETENTION_DAYS = 800
MIN_CORRELATION_N = 12

NUMERIC_FIELDS = (
    "opportunity_score",
    "opportunity_score_raw",
    "opportunity_timing_score",
    "fair_value_upside_pct",
    "margin_of_safety_pct",
    "qarp_score",
    "value_trap_risk_score",
    "confidence_score",
    "data_coverage_pct",
    "critical_metric_coverage_pct",
    "opportunity_rotation_breadth_pct",
    "opportunity_rotation_return_5d_pct",
    "opportunity_rotation_etf_evidence_count",
    "opportunity_market_breadth_20d_pct",
    "opportunity_market_return_5d_pct",
    "opportunity_market_return_20d_pct",
    "opportunity_market_regime_evidence_count",
    "opportunity_event_risk_days",
    "opportunity_revision_evidence_age_days",
    "opportunity_revision_evidence_coverage_pct",
    "opportunity_valuation_method_count",
    "opportunity_valuation_dispersion_pct",
)
SLEEVE_FIELDS = ("strength", "asymmetry", "inflection")


def num(v):
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def load_json(path, fallback):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else fallback
    except Exception:
        return fallback


def current_rows():
    payload = load_json(INDEX, {})
    out = {}
    for row in payload.get("stocks") or []:
        if not isinstance(row, dict):
            continue
        ticker = str(row.get("ticker") or "").strip().upper()
        price = num(row.get("current_price"))
        opp = num(row.get("opportunity_score"))
        if not ticker or price is None or price <= 0 or opp is None:
            continue
        if row.get("opportunity_eligible") is not True:
            continue
        if str(row.get("quote_type") or "").upper() in {"ETF", "CRYPTO", "CRYPTOCURRENCY", "FUND", "MUTUALFUND"}:
            continue
        if str(row.get("pipeline_status") or "") in {"equity_catalog_only", "equity_carried_forward"}:
            continue
        out[ticker] = row
    return out


def outcome_price_rows():
    """All current valid equity prices, independent of today's Discovery eligibility.

    Eligibility is frozen at the *selection* date. Filtering this lookup by
    current eligibility would selectively drop past winners/losers when their
    investment thesis or risk gate changes (survivorship bias).
    """
    payload = load_json(INDEX, {})
    out = {}
    for row in payload.get("stocks") or []:
        if not isinstance(row, dict):
            continue
        ticker = str(row.get("ticker") or "").strip().upper()
        price = num(row.get("current_price"))
        if not ticker or price is None or price <= 0:
            continue
        if str(row.get("quote_type") or "").upper() in {
            "ETF", "CRYPTO", "CRYPTOCURRENCY", "FUND", "MUTUALFUND"
        }:
            continue
        if str(row.get("pipeline_status") or "") in {
            "equity_catalog_only", "equity_carried_forward"
        }:
            continue
        out[ticker] = row
    return out


def make_observation(row):
    sleeves = row.get("opportunity_sleeves") or {}
    return {
        "price": num(row.get("current_price")),
        "sector": str(row.get("sector") or "Unknown"),
        "score_model": str(row.get("score_model") or "general"),
        "opportunity_label": str(row.get("opportunity_label") or ""),
        "opportunity_upside_support": str(row.get("opportunity_upside_support") or "unavailable"),
        "risk_gate": str(row.get("risk_gate") or "unknown"),
        "opportunity_rotation_theme": str(row.get("opportunity_rotation_theme") or ""),
        "opportunity_rotation_signal": str(row.get("opportunity_rotation_signal") or ""),
        "opportunity_rotation_etf_confirmed": row.get("opportunity_rotation_etf_confirmed"),
        "opportunity_rotation_etf_evidence_count": row.get("opportunity_rotation_etf_evidence_count"),
        "opportunity_market_regime": str(row.get("opportunity_market_regime") or ""),
        "opportunity_market_regime_source": str(row.get("opportunity_market_regime_source") or ""),
        "opportunity_event_risk": str(row.get("opportunity_event_risk") or "none"),
        "opportunity_event_risk_date": str(row.get("opportunity_event_risk_date") or ""),
        "opportunity_event_risk_source": str(row.get("opportunity_event_risk_source") or ""),
        "opportunity_revision_evidence": str(row.get("opportunity_revision_evidence") or "unavailable"),
        "opportunity_revision_evidence_confidence": str(row.get("opportunity_revision_evidence_confidence") or ""),
        "opportunity_revision_evidence_refresh_state": str(row.get("opportunity_revision_evidence_refresh_state") or ""),
        "opportunity_valuation_evidence": str(row.get("opportunity_valuation_evidence") or "unavailable"),
        **{field: num(row.get(field)) for field in NUMERIC_FIELDS},
        **{f"sleeve_{field}": num(sleeves.get(field)) for field in SLEEVE_FIELDS},
    }


def make_snapshot(today, rows):
    return {
        "date": today.isoformat(),
        "observations": {ticker: make_observation(row) for ticker, row in rows.items()},
    }


def outcome_key(cohort_date, horizon, ticker):
    return f"{cohort_date}|{int(horizon)}|{ticker}"


def materialise_outcomes(today, snapshots, rows, outcomes):
    existing = {
        outcome_key(x.get("cohort_date"), x.get("horizon_days"), x.get("ticker"))
        for x in outcomes if isinstance(x, dict)
    }
    added = 0
    for snap in snapshots:
        try:
            snap_date = dt.date.fromisoformat(str(snap.get("date")))
        except Exception:
            continue
        age = (today - snap_date).days
        observations = snap.get("observations") or {}
        for horizon in HORIZONS:
            if age < horizon or age > horizon + MAX_HORIZON_LATENESS_DAYS:
                continue
            for ticker, old in observations.items():
                key = outcome_key(snap["date"], horizon, ticker)
                if key in existing or not isinstance(old, dict):
                    continue
                now = rows.get(ticker)
                if not now:
                    continue
                p0 = num(old.get("price"))
                p1 = num(now.get("current_price"))
                opp = num(old.get("opportunity_score"))
                if p0 is None or p1 is None or p0 <= 0 or opp is None:
                    continue
                adjustment = corporate_action_adjusted_return(
                    ticker, snap["date"], today.isoformat(), p0, p1, rows
                )
                if adjustment is None:
                    continue
                item = {
                    "cohort_date": snap["date"],
                    "evaluated_date": today.isoformat(),
                    "actual_days": age,
                    "horizon_days": horizon,
                    "ticker": ticker,
                    "start_price": round(p0, 8),
                    "end_price": round(p1, 8),
                    "return_pct": round(adjustment["return_pct"], 6),
                    "raw_return_pct": round(adjustment["raw_return_pct"], 6),
                    "split_adjustment_factor": adjustment["split_adjustment_factor"],
                    "distribution_value_per_parent": adjustment["distribution_value_per_parent"],
                    "corporate_action_adjusted": adjustment["corporate_action_adjusted"],
                    "corporate_action_unresolved": adjustment["corporate_action_unresolved"],
                    "unresolved_distributions": adjustment["unresolved_distributions"],
                    "validation_eligible": adjustment["validation_eligible"],
                    **{k: v for k, v in old.items() if k != "price"},
                }
                outcomes.append(item)
                existing.add(key)
                added += 1
    return added


def _rank(values):
    indexed = sorted(enumerate(values), key=lambda x: x[1])
    out = [0.0] * len(values)
    i = 0
    while i < len(indexed):
        j = i + 1
        while j < len(indexed) and indexed[j][1] == indexed[i][1]:
            j += 1
        avg = (i + j - 1) / 2 + 1
        for k in range(i, j):
            out[indexed[k][0]] = avg
        i = j
    return out


def spearman(pairs):
    clean = [(num(a), num(b)) for a, b in pairs]
    clean = [(a, b) for a, b in clean if a is not None and b is not None]
    if len(clean) < MIN_CORRELATION_N:
        return None
    a, b = zip(*clean)
    ra, rb = _rank(a), _rank(b)
    am, bm = statistics.mean(ra), statistics.mean(rb)
    cov = sum((x-am)*(y-bm) for x, y in zip(ra, rb))
    va = sum((x-am)**2 for x in ra)
    vb = sum((y-bm)**2 for y in rb)
    return cov / math.sqrt(va * vb) if va > 0 and vb > 0 else None


def median(values):
    vals = [num(v) for v in values]
    vals = [v for v in vals if v is not None]
    return statistics.median(vals) if vals else None


def mean(values):
    vals = [num(v) for v in values]
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals) if vals else None


def quintile_spread(vals):
    rows = [x for x in vals if num(x.get("opportunity_score")) is not None and num(x.get("return_pct")) is not None]
    if len(rows) < 10:
        return None
    rows.sort(key=lambda x: num(x.get("opportunity_score")))
    q = max(1, len(rows) // 5)
    low = rows[:q]
    high = rows[-q:]
    hi = median([x.get("return_pct") for x in high])
    lo = median([x.get("return_pct") for x in low])
    return (hi - lo) if hi is not None and lo is not None else None


def group_breakdown(vals, field):
    groups = defaultdict(list)
    for item in vals:
        key = str(item.get(field) or "unknown")
        groups[key].append(item)
    out = {}
    for key, rows in sorted(groups.items()):
        rets = [num(x.get("return_pct")) for x in rows]
        rets = [x for x in rets if x is not None]
        if not rets:
            continue
        out[key] = {
            "n": len(rets),
            "mean_return_pct": round(sum(rets) / len(rets), 2),
            "median_return_pct": round(statistics.median(rets), 2),
            "positive_return_pct": round(sum(1 for x in rets if x > 0) / len(rets) * 100.0, 1),
        }
    return out


def cohort_summaries(vals):
    groups = defaultdict(list)
    for item in vals:
        groups[str(item.get("cohort_date") or "")].append(item)
    out = []
    for date, rows in sorted(groups.items()):
        ic = spearman([(x.get("opportunity_score"), x.get("return_pct")) for x in rows])
        spread = quintile_spread(rows)
        out.append({
            "cohort_date": date,
            "n": len(rows),
            "rank_information_coefficient": round(ic, 4) if ic is not None else None,
            "median_top_minus_bottom_pct": round(spread, 2) if spread is not None else None,
            "median_return_pct": round(median([x.get("return_pct") for x in rows]), 2) if rows else None,
        })
    return out


def validation_status(cohort_count):
    if cohort_count >= 8:
        return "multiple_cohorts_available"
    if cohort_count >= 3:
        return "early_evidence"
    return "collecting_evidence"


def expected_matured_count(today, snapshots, horizon):
    count = 0
    for snap in snapshots:
        try:
            age = (today - dt.date.fromisoformat(str(snap.get("date")))).days
        except Exception:
            continue
        if age >= horizon:
            count += 1
    return count


def observation_capture(today, snapshots, outcomes, horizon):
    """Measure asset-level prospective coverage, not merely cohort presence.

    One successfully priced ticker must not make an entire 1,000-name cohort
    look 100% captured. Historical snapshots remain frozen and missing prices
    are not imputed as zero returns.
    """
    expected = set()
    for snap in snapshots:
        if not isinstance(snap, dict):
            continue
        try:
            cohort = str(snap.get("date"))
            age = (today - dt.date.fromisoformat(cohort)).days
        except (TypeError, ValueError):
            continue
        if age < horizon:
            continue
        observations = snap.get("observations") or {}
        if not isinstance(observations, dict):
            continue
        for ticker, observation in observations.items():
            if isinstance(observation, dict):
                expected.add(outcome_key(cohort, horizon, ticker))

    realised = {
        outcome_key(item.get("cohort_date"), horizon, item.get("ticker"))
        for item in outcomes
        if isinstance(item, dict) and int(item.get("horizon_days") or 0) == horizon
        and outcome_key(item.get("cohort_date"), horizon, item.get("ticker")) in expected
    }
    validated = {
        outcome_key(item.get("cohort_date"), horizon, item.get("ticker"))
        for item in outcomes
        if isinstance(item, dict) and int(item.get("horizon_days") or 0) == horizon
        and item.get("validation_eligible") is True
        and num(item.get("return_pct")) is not None
        and outcome_key(item.get("cohort_date"), horizon, item.get("ticker")) in expected
    }
    count = len(expected)
    return {
        "expected_matured_observations": count,
        "realised_matured_observations": len(realised),
        "missing_matured_observations": count - len(realised),
        "observation_capture_pct": round(100.0 * len(realised) / count, 1) if count else None,
        "validated_matured_observations": len(validated),
        "unvalidated_matured_observations": len(realised - validated),
        "validated_capture_pct": round(100.0 * len(validated) / count, 1) if count else None,
    }


def missing_outcome_diagnostics(today, snapshots, outcomes, horizon, current_prices, sample_limit=12):
    """Audit missing future returns without assuming a delisting or a loss.

    Current ticker absence only means the canonical current index cannot supply
    a usable price. It is not evidence of bankruptcy, a delisting or -100% return.
    """
    recorded = {
        outcome_key(x.get("cohort_date"), horizon, x.get("ticker"))
        for x in outcomes if isinstance(x, dict)
        and int(x.get("horizon_days") or 0) == horizon
    }
    missing = []
    recoverable = 0
    unavailable = 0
    window_expired = 0
    for snap in snapshots:
        if not isinstance(snap, dict):
            continue
        try:
            age = (today - dt.date.fromisoformat(str(snap.get("date")))).days
        except (TypeError, ValueError):
            continue
        if age < horizon:
            continue
        for ticker, observation in (snap.get("observations") or {}).items():
            if not isinstance(observation, dict):
                continue
            key = outcome_key(snap["date"], horizon, ticker)
            if key in recorded:
                continue
            is_priced = ticker in current_prices
            is_late = age > horizon + MAX_HORIZON_LATENESS_DAYS
            recoverable += int(is_priced and not is_late)
            unavailable += int(not is_priced)
            window_expired += int(is_late)
            missing.append({
                "cohort_date": snap["date"], "ticker": ticker,
                "price_available_now": is_priced,
                "capture_window_expired": is_late,
            })
    return {
        "missing_outcome_count": len(missing),
        "missing_price_now_count": unavailable,
        "price_available_within_window_count": recoverable,
        "capture_window_expired_count": window_expired,
        "missing_outcome_samples": missing[:max(0, sample_limit)],
        "delisting_status": "unverified",
    }


def maturity_dates(today, snapshots, horizon):
    dates = []
    for snap in snapshots:
        try:
            dates.append(dt.date.fromisoformat(str(snap.get("date"))))
        except Exception:
            continue
    if not dates:
        return None, None
    maturity = sorted(d + dt.timedelta(days=horizon) for d in dates)
    pending = [d for d in maturity if d > today]
    return maturity[0], (pending[0] if pending else None)


def summarize_horizon(vals, expected_matured_cohorts=0):
    cohorts = cohort_summaries(vals)
    ics = [num(x.get("rank_information_coefficient")) for x in cohorts]
    ics = [x for x in ics if x is not None]
    spreads = [num(x.get("median_top_minus_bottom_pct")) for x in cohorts]
    spreads = [x for x in spreads if x is not None]
    overall_ic = spearman([(x.get("opportunity_score"), x.get("return_pct")) for x in vals])
    return {
        "n": len(vals),
        "cohort_count": len(cohorts),
        "expected_matured_cohorts": expected_matured_cohorts,
        "cohort_capture_pct": round(len(cohorts) / expected_matured_cohorts * 100.0, 1) if expected_matured_cohorts else None,
        "rank_information_coefficient": round(overall_ic, 4) if overall_ic is not None else None,
        "median_cohort_rank_ic": round(statistics.median(ics), 4) if ics else None,
        "positive_ic_cohorts": sum(1 for x in ics if x > 0),
        "median_cohort_top_minus_bottom_pct": round(statistics.median(spreads), 2) if spreads else None,
        "positive_spread_cohorts": sum(1 for x in spreads if x > 0),
        "median_return_pct": round(median([x.get("return_pct") for x in vals]), 2) if vals else None,
        "by_upside_support": group_breakdown(vals, "opportunity_upside_support"),
        "by_label": group_breakdown(vals, "opportunity_label"),
        "by_rotation_signal": group_breakdown(vals, "opportunity_rotation_signal"),
        "by_rotation_etf_confirmation": group_breakdown(vals, "opportunity_rotation_etf_confirmed"),
        "by_market_regime": group_breakdown(vals, "opportunity_market_regime"),
        "by_event_risk": group_breakdown(vals, "opportunity_event_risk"),
        "by_revision_evidence": group_breakdown(vals, "opportunity_revision_evidence"),
        "by_valuation_evidence": group_breakdown(vals, "opportunity_valuation_evidence"),
        "by_sector": group_breakdown(vals, "sector"),
        "cohorts": cohorts,
        "status": validation_status(len(cohorts)),
    }


def evidence_policy(report_horizons):
    mature = [
        int(h) for h, pack in report_horizons.items()
        if (pack.get("cohort_count") or 0) >= 8
        and (pack.get("validated_capture_pct") or 0) >= 80
        and (pack.get("n") or 0) >= 100
    ]
    return {
        "status": "observe_only" if len(mature) < 2 else "review_allowed",
        "production_rules_frozen": True,
        "mature_horizons": mature,
        "rule": "Opportunity weights/gates are never auto-tuned. Review requires >=8 mature cohorts, >=100 validated outcomes and >=80% validated observation capture on at least two horizons.",
    }


def main():
    today = dt.date.today()
    rows = current_rows()
    outcome_prices = outcome_price_rows()
    history = load_json(HISTORY, {"schema_version": 1, "snapshots": [], "outcomes": []})
    snapshots = history.setdefault("snapshots", [])
    outcomes = history.setdefault("outcomes", [])

    latest_date = None
    if snapshots:
        try:
            latest_date = max(dt.date.fromisoformat(str(s.get("date"))) for s in snapshots)
        except Exception:
            latest_date = None
    if latest_date is None or (today - latest_date).days >= 7:
        snapshots.append(make_snapshot(today, rows))

    cutoff = today - dt.timedelta(days=RETENTION_DAYS)
    snapshots[:] = [s for s in snapshots if isinstance(s, dict) and dt.date.fromisoformat(str(s.get("date"))) >= cutoff]
    outcomes[:] = [x for x in outcomes if isinstance(x, dict) and dt.date.fromisoformat(str(x.get("cohort_date"))) >= cutoff]

    added = materialise_outcomes(today, snapshots, outcome_prices, outcomes)

    horizon_report = {}
    for horizon in HORIZONS:
        vals = [x for x in outcomes if int(x.get("horizon_days") or 0) == horizon
                and x.get("validation_eligible") is True]
        expected = expected_matured_count(today, snapshots, horizon)
        pack = summarize_horizon(vals, expected)
        pack.update(observation_capture(today, snapshots, outcomes, horizon))
        pack.update(missing_outcome_diagnostics(today, snapshots, outcomes, horizon, outcome_prices))
        pack["legacy_or_unresolved_outcomes"] = sum(
            1 for x in outcomes if int(x.get("horizon_days") or 0) == horizon
            and x.get("validation_eligible") is not True
        )
        first, pending = maturity_dates(today, snapshots, horizon)
        pack["first_possible_maturity_date"] = first.isoformat() if first else None
        pack["next_pending_maturity_date"] = pending.isoformat() if pending else None
        horizon_report[str(horizon)] = pack

    history.update({
        "schema_version": 1,
        "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "snapshot_count": len(snapshots),
        "outcome_count": len(outcomes),
    })
    HISTORY.write_text(json.dumps(history, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n", encoding="utf-8")

    report = {
        "schema_version": 1,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "methodology": "prospective weekly Opportunity cohorts; persistent realised price returns; no historical reconstruction",
        "horizons_days": list(HORIZONS),
        "snapshots_available": len(snapshots),
        "realised_outcomes": len(outcomes),
        "new_outcomes_this_run": added,
        "horizons": horizon_report,
        "evidence_policy": evidence_policy(horizon_report),
        "interpretation": {
            "rank_ic": "Spearman correlation between Opportunity score known at cohort date and realised forward return.",
            "top_minus_bottom": "Median return spread between highest and lowest Opportunity-score quintiles.",
            "observation_capture": "Recorded observation coverage counts legacy outcomes; validated_capture_pct counts only corporate-action-validated results and is used in evidence policy. Neither imputes missing/delisted returns.",
            "upside_support": "Compares realised returns for strong/moderate/weak/negative/unavailable support known at cohort date.",
            "no_auto_tuning": "This report is diagnostic only and never changes production Opportunity rules.",
            "return_basis": "Price returns adjusted for explicitly registered splits/spin-offs using shared Score validation rules. Dividends and unregistered corporate actions remain unaccounted for; NOT total shareholder returns.",
            "legacy": "Existing historical outcomes without validation_eligible are preserved but excluded from adjusted ranking statistics; do not mislabel them as action-adjusted.",
            "survivorship": "Missing or delisted tickers are not given synthetic returns; observation capture must be checked before interpreting IC or spread.",
            "missing_outcomes": "Missing price is not evidence of delisting. Missing outcomes are itemised separately by cohort and capture-window status, without invented zero or -100% returns.",
        },
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
