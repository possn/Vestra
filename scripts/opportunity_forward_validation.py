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
    from scripts.discovery_dividend_evidence import validated_events, documented_dividend_cash, load_verified_ledger
except ModuleNotFoundError:
    from discovery_dividend_evidence import validated_events, documented_dividend_cash, load_verified_ledger

try:
    from scripts.score_forward_validation import corporate_action_adjusted_return
except ModuleNotFoundError:
    from score_forward_validation import corporate_action_adjusted_return

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "data" / "stocks-index.json"
HISTORY = ROOT / "data" / "opportunity_validation_history.json"
REPORT = ROOT / "data" / "opportunity_validation_report.json"
DIVIDEND_EVIDENCE = ROOT / "data" / "verified_dividend_events.json"
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



def load_validation_history(path):
    """Fail closed on missing/corrupt prospective history; never reset it silently.

    The frozen weekly cohorts and realised outcomes are cumulative evidence.
    Replacing either with an empty fallback on read failure irreversibly
    corrupts the forward validation dataset when the workflow publishes.
    Initial bootstrapping must create an explicit valid schema-1 ledger.
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"Prospective history unavailable: {path}") from exc
    try:
        data = json.loads(raw)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Prospective history is invalid JSON: {path}") from exc
    if (not isinstance(data, dict) or data.get("schema_version") != 1
            or not isinstance(data.get("snapshots"), list)
            or not isinstance(data.get("outcomes"), list)):
        raise ValueError(f"Unexpected prospective history schema: {path}")
    return data


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


def terminal_quote_catalog():
    """Describe why frozen tickers lack a currently usable outcome price.

    This catalog is diagnostic only; missing from the current index is NOT
    evidence of delisting, bankruptcy, or a zero/negative return.
    """
    payload = load_json(INDEX, {})
    catalog = defaultdict(list)
    for row in payload.get("stocks") or []:
        if not isinstance(row, dict):
            continue
        ticker = str(row.get("ticker") or "").strip().upper()
        if ticker:
            catalog[ticker].append(row)
    return dict(catalog)


def missing_terminal_quote_reason(ticker, current_prices, catalog):
    if ticker in current_prices:
        return "usable_quote_not_captured"
    if catalog is None:
        return "unclassified_no_catalog"
    matches = catalog.get(ticker) or []
    if not matches:
        return "absent_from_current_index"
    if len(matches) != 1:
        return "ambiguous_multiple_index_rows"
    row = matches[0]
    quote_type = str(row.get("quote_type") or "").upper()
    if quote_type in {"ETF", "CRYPTO", "CRYPTOCURRENCY", "FUND", "MUTUALFUND"}:
        return "currently_non_equity_type"
    if str(row.get("pipeline_status") or "") in {"equity_catalog_only", "equity_carried_forward"}:
        return "quote_excluded_stale_or_catalog"
    price = num(row.get("current_price"))
    if price is None or price <= 0:
        return "invalid_or_missing_current_price"
    return "other_current_index_exclusion"


def make_observation(row):
    sleeves = row.get("opportunity_sleeves") or {}
    return {
        "price": num(row.get("current_price")),
        "currency": str(row.get("currency") or "").strip().upper(),
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


def outcome_has_verified_evaluation_window(item, horizon, today):
    """A claimed prospective return must be observed within its frozen window.

    Retrospective prices, premature evaluations, absent evaluation dates and
    inconsistent reported actual_days do not establish horizon-specific alpha.
    """
    try:
        cohort = dt.date.fromisoformat(str(item["cohort_date"]))
        evaluated = dt.date.fromisoformat(str(item["evaluated_date"]))
        actual = (evaluated - cohort).days
        if evaluated > today or not (horizon <= actual <= horizon + MAX_HORIZON_LATENESS_DAYS):
            return False
        recorded = item.get("actual_days")
        if recorded is not None and (isinstance(recorded, bool) or
                                      int(recorded) != actual):
            return False
        return True
    except (KeyError, ValueError, TypeError, OverflowError):
        return False


def outcome_key(cohort_date, horizon, ticker):
    return f"{cohort_date}|{int(horizon)}|{ticker}"


def materialise_outcomes(today, snapshots, rows, outcomes, dividend_events=None):
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
                # Documented cash is diagnostic, not proof of complete dividend coverage.
                cash = documented_dividend_cash(
                    ticker, snap["date"], today.isoformat(),
                    old.get("currency"), dividend_events or [],
                )
                # Price-only forward returns require comparable quote units.
                # The dividend check alone was insufficient: a currency change
                # with no documented dividends could masquerade as alpha.
                initial_currency = str(old.get("currency") or "").strip().upper()
                terminal_currency = str(now.get("currency") or "").strip().upper()
                currency_comparable = bool(initial_currency and terminal_currency
                                           and initial_currency == terminal_currency)
                if not currency_comparable:
                    # Keep a diagnostic outcome, but never rank it as validated.
                    # No FX conversion can be inferred without point-in-time rates.
                    adjustment = {**adjustment, "validation_eligible": False}
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
                    "quote_currency_comparable": currency_comparable,
                    "terminal_quote_currency": terminal_currency or None,
                    "documented_dividend_event_count": cash["event_count"],
                    "documented_dividend_cash_per_share": cash["cash_per_terminal_share"],
                    "documented_dividend_sources": cash["source_urls"],
                    "documented_cash_inclusive_return_pct": (
                        round((adjustment["return_pct"] / 100.0
                               + cash["cash_per_terminal_share"]
                               / (p0 * adjustment["split_adjustment_factor"])) * 100.0, 6)
                        if cash["event_count"] and adjustment["validation_eligible"] else None
                    ),
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
        and outcome_has_verified_evaluation_window(item, horizon, today)
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


def outcome_exclusion_reasons(today, snapshots, outcomes, horizon):
    """Explain why recorded prospective outcomes are NOT validation-eligible.

    This is a disjoint accounting of all unique recorded keys belonging to
    matured frozen cohorts. Legacy results are NOT retroactively revalidated.
    Invalid numeric returns are excluded even if a stale flag says eligible.
    """
    expected = set()
    cohort_expected = {}
    for snap in snapshots:
        if not isinstance(snap, dict):
            continue
        try:
            cohort = str(snap["date"])
            if (today - dt.date.fromisoformat(cohort)).days < horizon:
                continue
        except (KeyError, TypeError, ValueError):
            continue
        rows = snap.get("observations") or {}
        if not isinstance(rows, dict):
            continue
        cohort_keys = cohort_expected.setdefault(cohort, set())
        for ticker, old in rows.items():
            if isinstance(old, dict):
                key = outcome_key(cohort, horizon, ticker)
                expected.add(key)
                cohort_keys.add(key)

    categories = {
        "eligible": 0,
        "legacy_missing_eligibility": 0,
        "invalid_return": 0,
        "invalid_evaluation_window": 0,
        "unresolved_corporate_action": 0,
        "incomparable_quote_currency": 0,
        "explicitly_ineligible_other": 0,
    }
    # Group unique cohort/horizon/ticker keys before determining eligibility.
    # The original order of historical outcomes must never change diagnostics.
    grouped = {}
    for item in outcomes:
        if not isinstance(item, dict):
            continue
        try:
            if int(item.get("horizon_days") or 0) != horizon:
                continue
        except (TypeError, ValueError):
            continue
        key = outcome_key(item.get("cohort_date"), horizon, item.get("ticker"))
        if key in expected:
            grouped.setdefault(key, []).append(item)
    ignored_duplicates = sum(len(items) - 1 for items in grouped.values())
    duplicate_conflicts = 0
    by_cohort = {
        date: {"cohort_date": date, "expected": len(keys), "recorded": 0,
               "duplicate_records_ignored": 0, "duplicate_conflicts": 0,
               "exclusion_reasons": {name: 0 for name in categories}}
        for date, keys in cohort_expected.items()
    }
    for key, items in grouped.items():
        cohort_row = by_cohort[str(items[0].get("cohort_date"))]
        cohort_row["recorded"] += 1
        cohort_row["duplicate_records_ignored"] += len(items) - 1
        # Match observation_capture's any-explicit-valid rule, but expose
        # disagreements rather than treating multiple records as independent.
        eligible = [
            item for item in items
            if item.get("validation_eligible") is True
            and num(item.get("return_pct")) is not None
            and outcome_has_verified_evaluation_window(item, horizon, today)
        ]
        signatures = {
            (item.get("validation_eligible"), num(item.get("return_pct")))
            for item in items
        }
        if len(signatures) > 1:
            duplicate_conflicts += 1
            cohort_row["duplicate_conflicts"] += 1
        if eligible:
            category = "eligible"
        elif all(num(item.get("return_pct")) is None for item in items):
            category = "invalid_return"
        elif all(item.get("validation_eligible") is None for item in items):
            category = "legacy_missing_eligibility"
        elif any(item.get("validation_eligible") is True
                 and num(item.get("return_pct")) is not None
                 and not outcome_has_verified_evaluation_window(item, horizon, today)
                 for item in items):
            category = "invalid_evaluation_window"
        elif any(item.get("corporate_action_unresolved") is True or
                 item.get("unresolved_distributions") for item in items):
            category = "unresolved_corporate_action"
        elif any(item.get("quote_currency_comparable") is False for item in items):
            category = "incomparable_quote_currency"
        else:
            category = "explicitly_ineligible_other"
        categories[category] += 1
        cohort_row["exclusion_reasons"][category] += 1

    for row in by_cohort.values():
        row["missing"] = row["expected"] - row["recorded"]
        row["validated_capture_pct"] = (
            round(100.0 * row["exclusion_reasons"]["eligible"] / row["expected"], 1)
            if row["expected"] else None
        )
        row["unvalidated_recorded"] = (
            row["recorded"] - row["exclusion_reasons"]["eligible"]
        )

    return {
        "cohort_exclusion_breakdown": [
            by_cohort[date] for date in sorted(by_cohort)
        ],
        "scope": "unique recorded outcomes from matured frozen cohorts only",
        "expected_observations": len(expected),
        "recorded_observations": len(grouped),
        "missing_observations": len(expected) - len(grouped),
        "duplicate_records_ignored": ignored_duplicates,
        "duplicate_conflict_keys": duplicate_conflicts,
        "exclusion_reasons": categories,
        "unvalidated_recorded_observations": len(grouped) - categories["eligible"],
        "classification": "diagnostic_only_no_backfill",
        "interpretation": "Historical records without explicit corporate-action eligibility remain unvalidated. Duplicate conflicts are counted and must be investigated; neither duplicate outcomes nor missing prices prove alpha or delisting.",
    }


def score_quintile_capture(today, snapshots, outcomes, horizon):
    """Attrition by ORIGINAL cohort score rank, never by surviving returns.

    For each matured cohort, assign every frozen scored observation to one of
    five near-equal bins (rank ascending, deterministic ticker tie-break).
    Outcomes must match frozen cohort+ticker; duplicate records count once.
    Missing/invalid scores are reported separately, never silently discarded.
    No missing terminal return is imputed, and no alpha is inferred.
    """
    recorded = set()
    validated = set()
    for result in outcomes:
        if not isinstance(result, dict):
            continue
        try:
            if int(result.get("horizon_days") or 0) != horizon:
                continue
        except (TypeError, ValueError):
            continue
        key = outcome_key(result.get("cohort_date"), horizon, result.get("ticker"))
        recorded.add(key)
        if (result.get("validation_eligible") is True
                and num(result.get("return_pct")) is not None
                and outcome_has_verified_evaluation_window(result, horizon, today)):
            validated.add(key)

    bins = [{"quintile": q, "expected": 0, "recorded": 0, "validated": 0}
            for q in range(1, 6)]
    omitted_score = 0
    matured_cohorts = 0
    for snap in snapshots:
        if not isinstance(snap, dict):
            continue
        try:
            cohort = str(snap["date"])
            age = (today - dt.date.fromisoformat(cohort)).days
        except (ValueError, TypeError, KeyError):
            continue
        if age < horizon:
            continue
        observations = snap.get("observations") or {}
        if not isinstance(observations, dict):
            continue
        matured_cohorts += 1
        scored = []
        for ticker, observation in observations.items():
            if not isinstance(observation, dict):
                continue
            score = num(observation.get("opportunity_score"))
            if score is None:
                omitted_score += 1
                continue
            scored.append((score, str(ticker)))
        scored.sort(key=lambda item: (item[0], item[1]))
        n = len(scored)
        for i, (score, ticker) in enumerate(scored):
            # Rank grouping has deterministic ties and never depends on outcome.
            q = min(4, (5 * i) // n)
            item = bins[q]
            item["expected"] += 1
            key = outcome_key(cohort, horizon, ticker)
            item["recorded"] += int(key in recorded)
            item["validated"] += int(key in validated)

    for item in bins:
        expected = item["expected"]
        item["missing"] = expected - item["recorded"]
        item["unvalidated"] = item["recorded"] - item["validated"]
        item["validated_capture_pct"] = (
            round(100 * item["validated"] / expected, 1) if expected else None
        )
    nonempty = [item for item in bins if item["expected"]]
    coverage = [item["validated_capture_pct"] for item in nonempty]
    return {
        "method": "quintiles of all frozen scored observations, ascending original opportunity_score, within each matured cohort",
        "matured_cohorts": matured_cohorts,
        "missing_or_invalid_score_count": omitted_score,
        "quintiles": bins,
        "validated_capture_spread_pp": (
            round(max(coverage) - min(coverage), 1) if len(coverage) > 1 else None
        ),
        "selection_bias_status": "unresolved" if matured_cohorts else "not_yet_mature",
        "interpretation": "Diagnostic only: a correlation on surviving priced outcomes cannot establish prospective alpha. No missing outcome is imputed or delisting assumed.",
    }


def missing_outcome_diagnostics(today, snapshots, outcomes, horizon, current_prices, sample_limit=12, terminal_catalog=None):
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
    source_reasons = defaultdict(int)
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
            reason = missing_terminal_quote_reason(ticker, current_prices, terminal_catalog)
            source_reasons[reason] += 1
            recoverable += int(is_priced and not is_late)
            unavailable += int(not is_priced)
            window_expired += int(is_late)
            missing.append({
                "cohort_date": snap["date"], "ticker": ticker,
                "price_available_now": is_priced,
                "capture_window_expired": is_late,
                "terminal_quote_status": reason,
            })
    return {
        "missing_outcome_count": len(missing),
        "missing_price_now_count": unavailable,
        "price_available_within_window_count": recoverable,
        "capture_window_expired_count": window_expired,
        "missing_outcome_samples": missing[:max(0, sample_limit)],
        "missing_terminal_quote_reasons": dict(sorted(source_reasons.items())),
        "missing_terminal_quote_reason_total": sum(source_reasons.values()),
        "missing_terminal_quote_interpretation": "Describes current index evidence only. Absence or stale quotes cannot establish delisting, bankruptcy or realised loss; expired windows are never backfilled with today's price.",
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


def unique_validated_outcomes_for_statistics(today, snapshots, outcomes, horizon):
    """Use exactly one validated result per frozen matured cohort and ticker.

    Raw historical records are immutable. Conflicting duplicates are excluded
    from ranking statistics even if one record claims validation eligibility.
    Identical duplicates have weight one. Entries outside a frozen matured
    cohort cannot enter genuine out-of-sample evidence.
    """
    expected = set()
    for snap in snapshots:
        if not isinstance(snap, dict):
            continue
        try:
            cohort = str(snap["date"])
            age = (today - dt.date.fromisoformat(cohort)).days
        except (KeyError, TypeError, ValueError):
            continue
        if age < horizon:
            continue
        for ticker, obs in (snap.get("observations") or {}).items():
            if isinstance(obs, dict):
                expected.add(outcome_key(cohort, horizon, ticker))

    by_key = defaultdict(list)
    for item in outcomes:
        if not isinstance(item, dict):
            continue
        try:
            if int(item.get("horizon_days") or 0) != horizon:
                continue
        except (ValueError, TypeError):
            continue
        key = outcome_key(item.get("cohort_date"), horizon, item.get("ticker"))
        if key in expected:
            by_key[key].append(item)

    result = []
    conflicting_keys = 0
    deduplicated_records = 0
    invalid_evaluation_windows = 0
    for key in sorted(by_key):
        items = by_key[key]
        deduplicated_records += len(items) - 1
        # Treat disagreement about eligibility, returns, provenance or any
        # other recorded field as a conflict rather than selecting the winner.
        signatures = {json.dumps(item, sort_keys=True, ensure_ascii=False)
                      for item in items}
        if len(signatures) != 1:
            conflicting_keys += 1
            continue
        item = items[0]
        if not outcome_has_verified_evaluation_window(item, horizon, today):
            invalid_evaluation_windows += 1
            continue
        if item.get("validation_eligible") is True and num(item.get("return_pct")) is not None:
            result.append(item)
    return result, {
        "method": "one validated identical record per frozen matured cohort/horizon/ticker",
        "duplicate_records_ignored_for_statistics": deduplicated_records,
        "conflicting_outcome_keys_excluded_from_statistics": conflicting_keys,
        "validated_unique_outcomes_in_statistics": len(result),
        "invalid_or_unverified_evaluation_windows": invalid_evaluation_windows,
    }


def evidence_policy(report_horizons):
    """Only allow review when attrition is low across *every* frozen score rank.

    Overall capture can hide missing winners/losers concentrated in the highest
    or lowest scored quintile, manufacturing a persuasive but biased IC.
    """
    mature = []
    diagnostics = {}
    for h, pack in report_horizons.items():
        quintile_audit = pack.get("score_quintile_capture") or {}
        bins = quintile_audit.get("quintiles") or []
        valid_bins = (
            len(bins) == 5
            and all(
                isinstance(q, dict)
                and (q.get("expected") or 0) > 0
                and num(q.get("validated_capture_pct")) is not None
                and num(q.get("validated_capture_pct")) >= 80
                for q in bins
            )
        )
        reasons = []
        if (pack.get("cohort_count") or 0) < 8:
            reasons.append("fewer_than_8_matured_cohorts")
        if (pack.get("validated_capture_pct") or 0) < 80:
            reasons.append("overall_validated_capture_below_80pct")
        if (pack.get("n") or 0) < 100:
            reasons.append("fewer_than_100_validated_outcomes")
        if ((pack.get("outcome_exclusion_reasons") or {}).get("duplicate_conflict_keys") or 0) != 0:
            reasons.append("conflicting_duplicate_outcomes")
        if not valid_bins:
            reasons.append("frozen_score_quintile_capture_below_80pct_or_unavailable")
        diagnostics[str(h)] = {
            "review_eligible": not reasons,
            "reasons": reasons,
            "quintile_validated_capture_pct": [
                num(q.get("validated_capture_pct")) for q in bins
                if isinstance(q, dict)
            ],
        }
        if not reasons:
            mature.append(int(h))
    return {
        "status": "observe_only" if len(mature) < 2 else "review_allowed",
        "production_rules_frozen": True,
        "mature_horizons": mature,
        "horizon_review_diagnostics": diagnostics,
        "rule": "Opportunity weights/gates are never auto-tuned. Review requires >=8 mature cohorts, >=100 validated outcomes, >=80% validated observation capture overall AND in each frozen score quintile, and no conflicting duplicate records on at least two horizons.",
    }

def main():
    today = dt.date.today()
    rows = current_rows()
    outcome_prices = outcome_price_rows()
    quote_catalog = terminal_quote_catalog()
    history = load_validation_history(HISTORY)
    if not rows or not outcome_prices:
        raise ValueError("No usable current Discovery equities/prices; refusing to publish or alter frozen validation history")
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

    # Missing ledger means no documented payments. Invalid evidence stops publication.
    dividend_events = validated_events(load_verified_ledger(DIVIDEND_EVIDENCE))
    added = materialise_outcomes(today, snapshots, outcome_prices, outcomes, dividend_events)

    horizon_report = {}
    for horizon in HORIZONS:
        vals, unique_audit = unique_validated_outcomes_for_statistics(
            today, snapshots, outcomes, horizon
        )
        expected = expected_matured_count(today, snapshots, horizon)
        pack = summarize_horizon(vals, expected)
        pack["unique_outcome_statistics_audit"] = unique_audit
        pack.update(observation_capture(today, snapshots, outcomes, horizon))
        pack["score_quintile_capture"] = score_quintile_capture(today, snapshots, outcomes, horizon)
        pack["outcome_exclusion_reasons"] = outcome_exclusion_reasons(today, snapshots, outcomes, horizon)
        pack.update(missing_outcome_diagnostics(today, snapshots, outcomes, horizon, outcome_prices,
                                                terminal_catalog=quote_catalog))
        pack["documented_dividend_outcomes"] = sum(
            1 for x in vals if (x.get("documented_dividend_event_count") or 0) > 0
        )
        pack["documented_dividend_cash_is_complete"] = False
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
            "rank_ic": "Spearman correlation between Opportunity score known at cohort date and realised forward return. Statistics use unique matching frozen-cohort outcomes; conflicting duplicates are excluded.",
            "top_minus_bottom": "Median return spread between highest and lowest Opportunity-score quintiles.",
            "observation_capture": "Recorded observation coverage counts legacy outcomes; validated_capture_pct counts only corporate-action-validated results and is used in evidence policy. Neither imputes missing/delisted returns.",
            "upside_support": "Compares realised returns for strong/moderate/weak/negative/unavailable support known at cohort date.",
            "no_auto_tuning": "This report is diagnostic only and never changes production Opportunity rules.",
            "return_basis": "Ranking uses price returns with known splits/spin-offs. Separately, issuer-documented cash dividends may be shown for windows with verified payments; neither series proves full total shareholder return.",
            "dividend_evidence": "Only source-linked confirmed payments after the snapshot ex-date and paid by evaluation date are counted. Missing events are unknown, not zero; incomplete coverage never changes ranking IC or evidence readiness.",
            "legacy": "Existing historical outcomes without validation_eligible are preserved but excluded from adjusted ranking statistics; do not mislabel them as action-adjusted.",
            "survivorship": "Missing or delisted tickers are not given synthetic returns; observation capture must be checked before interpreting IC or spread.",
            "missing_outcomes": "Missing price is not evidence of delisting. Missing outcomes are itemised separately by cohort and capture-window status, without invented zero or -100% returns.",
        },
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
