"""Prospective, persistent validation of Vestra scores.

The tracker stores the score and dimensions that were genuinely known at each
weekly snapshot. When a snapshot reaches 4/12/24 weeks, the first eligible run
materialises a realised outcome and keeps it permanently. Reports are therefore
built from accumulated out-of-sample cohorts rather than only the cohort that
happens to mature on the current week.

Important: this validates ranking usefulness, not a promise of future returns.
Production score weights must not be optimised from a small number of overlapping
weekly cohorts.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "data" / "stocks-index.json"
HISTORY = ROOT / "data" / "score_validation_history.json"
REPORT = ROOT / "data" / "score_validation_report.json"
PEER_SHADOW = ROOT / "data" / "score_peer_shadow.json"
HORIZONS = (28, 84, 168)
MAX_HORIZON_LATENESS_DAYS = 10
RETENTION_DAYS = 800
MIN_CORRELATION_N = 20
MIN_BREAKDOWN_N = 30
REPORT_SCHEMA_VERSION = 5
REPORT_GENERATOR_VERSION = "score-forward-validation/cohort-aware-model-evidence-v3"
REPORT_VALIDITY_HOURS = 36

# Price-basis corporate actions that cross prospective validation windows.
# numerator/denominator describes NEW shares / OLD shares. A reverse split
# therefore increases the comparable pre-action price basis by denominator /
# numerator. Keep this registry explicit: extreme returns are never clipped
# merely because they are large.
VALIDATION_SPLITS = (
    {"ticker": "GOSS", "effective_date": "2026-09-11", "numerator": 1, "denominator": 80},
    {"ticker": "NFE", "effective_date": "2026-09-14", "numerator": 1, "denominator": 50},
    {"ticker": "ALCPB.PA", "effective_date": "2026-09-08", "numerator": 1, "denominator": 10},
)

# Stock distributions/spin-offs change shareholder value without changing the
# parent ticker's price basis. Total shareholder return must include the child.
VALIDATION_DISTRIBUTIONS = (
    {"parent": "CTVA", "effective_date": "2026-10-01", "child": "VYLR", "shares_per_parent": 1.0},
)
FIELDS = (
    "score", "quality_pct", "growth_pct", "balance_pct", "cashflow_pct",
    "value_pct", "execution_pct", "earnings_quality_pct",
    "capital_allocation_pct", "stability_pct",
)


def num(v):
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def split_price_basis_factor(ticker, start_date, end_date):
    """Return the factor that puts a pre-action price on the end-date share basis."""
    try:
        start = dt.date.fromisoformat(str(start_date)[:10])
        end = dt.date.fromisoformat(str(end_date)[:10])
    except Exception:
        return 1.0
    symbol = str(ticker or "").strip().upper()
    factor = 1.0
    for action in VALIDATION_SPLITS:
        if symbol != action["ticker"]:
            continue
        effective = dt.date.fromisoformat(action["effective_date"])
        if start < effective <= end:
            numerator = num(action.get("numerator"))
            denominator = num(action.get("denominator"))
            if numerator and denominator and numerator > 0 and denominator > 0:
                factor *= denominator / numerator
    return factor


def distribution_terminal_value(ticker, start_date, end_date, end_rows=None):
    """Return distributed child value per parent share, or unresolved metadata."""
    try:
        start = dt.date.fromisoformat(str(start_date)[:10])
        end = dt.date.fromisoformat(str(end_date)[:10])
    except Exception:
        return 0.0, []
    symbol = str(ticker or "").strip().upper()
    end_rows = end_rows or {}
    value = 0.0
    unresolved = []
    for action in VALIDATION_DISTRIBUTIONS:
        if symbol != action["parent"]:
            continue
        effective = dt.date.fromisoformat(action["effective_date"])
        if not (start < effective <= end):
            continue
        child = str(action["child"]).upper()
        row = end_rows.get(child) or {}
        child_price = num(row.get("current_price") if isinstance(row, dict) else row)
        shares = num(action.get("shares_per_parent"))
        if child_price is None or child_price < 0 or shares is None or shares <= 0:
            unresolved.append(child)
            continue
        value += child_price * shares
    return value, unresolved


def corporate_action_adjusted_return(
    ticker, start_date, end_date, start_price, end_price, end_rows=None
):
    p0, p1 = num(start_price), num(end_price)
    if p0 is None or p1 is None or p0 <= 0:
        return None
    split_factor = split_price_basis_factor(ticker, start_date, end_date)
    comparable_start = p0 * split_factor
    if comparable_start <= 0:
        return None
    distribution_value, unresolved = distribution_terminal_value(
        ticker, start_date, end_date, end_rows
    )
    raw_return = (p1 / p0 - 1.0) * 100.0
    if unresolved:
        return {
            "return_pct": raw_return,
            "raw_return_pct": raw_return,
            "split_adjustment_factor": split_factor,
            "distribution_value_per_parent": None,
            "corporate_action_adjusted": split_factor != 1.0,
            "corporate_action_unresolved": True,
            "unresolved_distributions": unresolved,
            "validation_eligible": False,
        }
    terminal_value = p1 + distribution_value
    return {
        "return_pct": (terminal_value / comparable_start - 1.0) * 100.0,
        "raw_return_pct": raw_return,
        "split_adjustment_factor": split_factor,
        "distribution_value_per_parent": distribution_value,
        "corporate_action_adjusted": split_factor != 1.0 or distribution_value != 0.0,
        "corporate_action_unresolved": False,
        "unresolved_distributions": [],
        "validation_eligible": True,
    }


def split_adjusted_return(ticker, start_date, end_date, start_price, end_price):
    """Backward-compatible split-only helper."""
    return corporate_action_adjusted_return(
        ticker, start_date, end_date, start_price, end_price, end_rows={}
    )


def _reference_prices_for_date(snapshots, date):
    for snap in snapshots or []:
        if str(snap.get("date") or "") != str(date or "")[:10]:
            continue
        out = {}
        for ticker, price in (snap.get("corporate_action_reference_prices") or {}).items():
            if num(price) is not None:
                out[str(ticker).upper()] = {"current_price": num(price)}
        for ticker, obs in (snap.get("observations") or {}).items():
            if isinstance(obs, dict) and num(obs.get("price")) is not None:
                out.setdefault(str(ticker).upper(), {"current_price": num(obs.get("price"))})
        return out
    return {}


def repair_persisted_split_outcomes(outcomes, snapshots=None):
    """Idempotently repair already-materialised outcomes that crossed known splits."""
    repaired = 0
    for item in outcomes:
        if not isinstance(item, dict):
            continue
        end_rows = _reference_prices_for_date(snapshots, item.get("evaluated_date"))
        result = corporate_action_adjusted_return(
            item.get("ticker"),
            item.get("cohort_date"),
            item.get("evaluated_date"),
            item.get("start_price"),
            item.get("end_price"),
            end_rows=end_rows,
        )
        if not result or (
            not result["corporate_action_adjusted"]
            and not result["corporate_action_unresolved"]
        ):
            continue
        new_return = round(result["return_pct"], 6)
        new_raw = round(result["raw_return_pct"], 6)
        changed = any([
            num(item.get("return_pct")) != new_return,
            num(item.get("raw_return_pct")) != new_raw,
            num(item.get("split_adjustment_factor")) != num(result["split_adjustment_factor"]),
            num(item.get("distribution_value_per_parent")) != num(result["distribution_value_per_parent"]),
            bool(item.get("corporate_action_adjusted")) != bool(result["corporate_action_adjusted"]),
            bool(item.get("corporate_action_unresolved")) != bool(result["corporate_action_unresolved"]),
            list(item.get("unresolved_distributions") or []) != list(result["unresolved_distributions"]),
            item.get("validation_eligible") is not result["validation_eligible"],
        ])
        if changed:
            repaired += 1
        item["raw_return_pct"] = new_raw
        item["return_pct"] = new_return
        item["split_adjustment_factor"] = result["split_adjustment_factor"]
        item["distribution_value_per_parent"] = result["distribution_value_per_parent"]
        item["corporate_action_adjusted"] = result["corporate_action_adjusted"]
        item["corporate_action_unresolved"] = result["corporate_action_unresolved"]
        item["unresolved_distributions"] = result["unresolved_distributions"]
        item["validation_eligible"] = result["validation_eligible"]
    return repaired


def rank(values):
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


def pearson(a, b):
    if len(a) < MIN_CORRELATION_N or len(a) != len(b):
        return None
    am = sum(a) / len(a)
    bm = sum(b) / len(b)
    cov = sum((x-am)*(y-bm) for x, y in zip(a, b))
    va = sum((x-am)**2 for x in a)
    vb = sum((y-bm)**2 for y in b)
    if va <= 0 or vb <= 0:
        return None
    return cov / math.sqrt(va*vb)


def spearman(pairs):
    clean = [(num(a), num(b)) for a, b in pairs]
    clean = [(a, b) for a, b in clean if a is not None and b is not None]
    if len(clean) < MIN_CORRELATION_N:
        return None
    return pearson(rank([a for a, _ in clean]), rank([b for _, b in clean]))


def load_json(path, fallback):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else fallback
    except Exception:
        return fallback


def current_rows():
    payload = load_json(INDEX, {})
    out = {}
    for r in payload.get("stocks") or []:
        if not isinstance(r, dict):
            continue
        ticker = str(r.get("ticker") or "").strip().upper()
        price = num(r.get("current_price"))
        score = num(r.get("score"))
        if not ticker or price is None or price <= 0 or score is None:
            continue
        if str(r.get("quote_type") or "").upper() in {"ETF", "CRYPTO", "FUND", "MUTUALFUND"}:
            continue
        if str(r.get("pipeline_status") or "") in {"equity_catalog_only", "equity_carried_forward"}:
            continue
        out[ticker] = r
    return out


def current_price_rows():
    """Live equity prices used to value outcomes and distributed child shares."""
    payload = load_json(INDEX, {})
    out = {}
    for r in payload.get("stocks") or []:
        if not isinstance(r, dict):
            continue
        ticker = str(r.get("ticker") or "").strip().upper()
        price = num(r.get("current_price"))
        if not ticker or price is None or price <= 0:
            continue
        if str(r.get("quote_type") or "").upper() in {"ETF", "CRYPTO", "FUND", "MUTUALFUND"}:
            continue
        if str(r.get("pipeline_status") or "") in {"equity_catalog_only", "equity_carried_forward"}:
            continue
        out[ticker] = r
    return out


def peer_shadow_state():
    payload = load_json(PEER_SHADOW, {})
    out = {}
    for row in payload.get("rows") or []:
        if not isinstance(row, dict):
            continue
        ticker = str(row.get("ticker") or "").strip().upper()
        score = num(row.get("peer_shadow_score"))
        if ticker and score is not None:
            out[ticker] = score
    role = str(payload.get("role") or "legacy_candidate")
    candidate_active = bool(payload.get("candidate_active")) and role == "candidate"
    candidate_id = payload.get("candidate_id") if candidate_active else None
    return {
        "scores": out,
        "role": role,
        "candidate_active": candidate_active,
        "candidate_id": candidate_id,
    }


def peer_shadow_scores():
    """Backward-compatible score map for tests and historical callers."""
    return peer_shadow_state()["scores"]


def make_snapshot(today, rows, shadow_scores=None, reference_prices=None):
    observations = {}
    shadow_scores = shadow_scores or {}
    for ticker, r in rows.items():
        observations[ticker] = {
            "price": num(r.get("current_price")),
            "sector": str(r.get("sector") or "Unknown"),
            "score_model": str(r.get("score_model") or "general"),
            "confidence_score": num(r.get("confidence_score")),
            "risk_gate": str(r.get("risk_gate") or "clear"),
            "peer_shadow_score": num(shadow_scores.get(ticker)),
            **{field: num(r.get(field)) for field in FIELDS},
        }
    reference_prices = reference_prices or {}
    corporate_action_reference_prices = {
        action["child"]: num((reference_prices.get(action["child"]) or {}).get("current_price"))
        for action in VALIDATION_DISTRIBUTIONS
        if num((reference_prices.get(action["child"]) or {}).get("current_price")) is not None
    }
    return {
        "date": today.isoformat(),
        "observations": observations,
        "corporate_action_reference_prices": corporate_action_reference_prices,
    }


def outcome_key(cohort_date, horizon, ticker):
    return f"{cohort_date}|{int(horizon)}|{ticker}"


def materialise_outcomes(today, snapshots, rows, outcomes):
    """Persist the first timely realised price for every matured cohort/ticker."""
    existing = {
        outcome_key(x.get("cohort_date"), x.get("horizon_days"), x.get("ticker"))
        for x in outcomes if isinstance(x, dict)
    }
    added = 0
    for snap in snapshots:
        try:
            snap_date = dt.date.fromisoformat(snap["date"])
        except Exception:
            continue
        age = (today - snap_date).days
        observations = snap.get("observations") or {}
        for horizon in HORIZONS:
            if age < horizon or age > horizon + MAX_HORIZON_LATENESS_DAYS:
                continue
            for ticker, old in observations.items():
                key = outcome_key(snap["date"], horizon, ticker)
                if key in existing:
                    continue
                now = rows.get(ticker)
                if not now:
                    continue
                p0 = num(old.get("price"))
                p1 = num(now.get("current_price"))
                score = num(old.get("score"))
                if p0 is None or p1 is None or p0 <= 0 or score is None:
                    continue
                adjusted = corporate_action_adjusted_return(
                    ticker, snap["date"], today.isoformat(), p0, p1, end_rows=rows
                )
                if not adjusted:
                    continue
                realised = adjusted["return_pct"]
                item = {
                    "cohort_date": snap["date"],
                    "evaluated_date": today.isoformat(),
                    "actual_days": age,
                    "horizon_days": horizon,
                    "ticker": ticker,
                    "start_price": round(p0, 8),
                    "end_price": round(p1, 8),
                    "return_pct": round(realised, 6),
                    "raw_return_pct": round(adjusted["raw_return_pct"], 6),
                    "split_adjustment_factor": adjusted["split_adjustment_factor"],
                    "corporate_action_adjusted": adjusted["corporate_action_adjusted"],
                    "distribution_value_per_parent": adjusted["distribution_value_per_parent"],
                    "corporate_action_unresolved": adjusted["corporate_action_unresolved"],
                    "unresolved_distributions": adjusted["unresolved_distributions"],
                    "validation_eligible": adjusted["validation_eligible"],
                    "sector": old.get("sector") or "Unknown",
                    "score_model": old.get("score_model") or "general",
                    "confidence_score": num(old.get("confidence_score")),
                    "risk_gate": old.get("risk_gate") or "clear",
                    "peer_shadow_score": num(old.get("peer_shadow_score")),
                    **{field: num(old.get(field)) for field in FIELDS},
                }
                outcomes.append(item)
                existing.add(key)
                added += 1
    return added


def finite_values(values):
    vals = [num(v) for v in values]
    return [v for v in vals if v is not None]


def mean(values):
    vals = finite_values(values)
    return sum(vals) / len(vals) if vals else None


def median(values):
    vals = finite_values(values)
    return statistics.median(vals) if vals else None


def winsorized_mean(values, tail_fraction=0.05):
    """Mean after symmetric tail clipping; diagnostic only, never mutates outcomes."""
    vals = sorted(finite_values(values))
    if not vals:
        return None
    if len(vals) < 20 or tail_fraction <= 0:
        return sum(vals) / len(vals)
    k = min(int(len(vals) * tail_fraction), (len(vals) - 1) // 2)
    if k <= 0:
        return sum(vals) / len(vals)
    low, high = vals[k], vals[-k - 1]
    clipped = [min(high, max(low, value)) for value in vals]
    return sum(clipped) / len(clipped)


def quintile_metrics(vals, score_field="score"):
    ordered = sorted(vals, key=lambda x: num(x.get(score_field)) if num(x.get(score_field)) is not None else -1e9, reverse=True)
    if not ordered:
        return {}
    q = max(1, len(ordered) // 5)
    top = [x.get("return_pct") for x in ordered[:q]]
    bottom = [x.get("return_pct") for x in ordered[-q:]]
    top_mean, bottom_mean = mean(top), mean(bottom)
    top_median, bottom_median = median(top), median(bottom)
    top_winsor, bottom_winsor = winsorized_mean(top), winsorized_mean(bottom)
    return {
        "top_quintile_mean_return_pct": top_mean,
        "bottom_quintile_mean_return_pct": bottom_mean,
        "top_minus_bottom_pct": top_mean - bottom_mean if top_mean is not None and bottom_mean is not None else None,
        "top_quintile_median_return_pct": top_median,
        "bottom_quintile_median_return_pct": bottom_median,
        "median_top_minus_bottom_pct": top_median - bottom_median if top_median is not None and bottom_median is not None else None,
        "top_quintile_winsorized_mean_return_pct": top_winsor,
        "bottom_quintile_winsorized_mean_return_pct": bottom_winsor,
        "winsorized_top_minus_bottom_pct": top_winsor - bottom_winsor if top_winsor is not None and bottom_winsor is not None else None,
    }


def metric_pack(vals, score_field="score"):
    ic = spearman([(x.get(score_field), x.get("return_pct")) for x in vals])
    quintiles = quintile_metrics(vals, score_field)
    return {
        "n": len(vals),
        "rank_information_coefficient": round(ic, 4) if ic is not None else None,
        **{
            key: round(value, 2) if value is not None else None
            for key, value in quintiles.items()
        },
    }


def factor_ics(vals):
    result = {}
    for field in FIELDS:
        ic = spearman([(x.get(field), x.get("return_pct")) for x in vals])
        result[field] = round(ic, 4) if ic is not None else None
    return result


def grouped_breakdown(vals, field):
    groups = defaultdict(list)
    for row in vals:
        groups[str(row.get(field) or "Unknown")].append(row)
    out = {}
    for key, rows in sorted(groups.items()):
        if len(rows) < MIN_BREAKDOWN_N:
            continue
        pack = metric_pack(rows)
        out[key] = pack
    return out


def cohort_summaries(vals):
    groups = defaultdict(list)
    for row in vals:
        groups[str(row.get("cohort_date"))].append(row)
    out = []
    for date, rows in sorted(groups.items()):
        pack = metric_pack(rows)
        out.append({"cohort_date": date, **pack})
    return out


def cohort_stability_diagnostics(cohorts):
    """Describe cross-cohort stability without creating a tuning rule."""
    ic_values = []
    spread_values = []
    joint = []
    for cohort in cohorts:
        ic = num(cohort.get("rank_information_coefficient"))
        spread = num(cohort.get("winsorized_top_minus_bottom_pct"))
        if ic is not None:
            ic_values.append(ic)
        if spread is not None:
            spread_values.append(spread)
        if ic is not None and spread is not None:
            joint.append((ic, spread))

    def dispersion(values, digits):
        if not values:
            return {
                "min": None,
                "max": None,
                "range": None,
                "median_absolute_deviation": None,
            }
        median = statistics.median(values)
        return {
            "min": round(min(values), digits),
            "max": round(max(values), digits),
            "range": round(max(values) - min(values), digits),
            "median_absolute_deviation": round(
                statistics.median(abs(x - median) for x in values),
                digits,
            ),
        }

    joint_positive = sum(1 for ic, spread in joint if ic > 0 and spread > 0)
    return {
        "rank_ic": dispersion(ic_values, 4),
        "robust_spread_pct": dispersion(spread_values, 2),
        "cohorts_with_both_metrics": len(joint),
        "joint_positive_cohorts": joint_positive,
        "joint_positive_share_pct": (
            round(joint_positive / len(joint) * 100, 1) if joint else None
        ),
        "interpretation": (
            "Descriptive only. Dispersion and sign consistency across matured cohorts "
            "must accumulate prospectively and must not be used to retune production weights "
            "from a small sample."
        ),
    }


def cohort_composition_diagnostics(rows):
    """Describe whether adjacent prospective cohorts contain broadly the same names."""
    groups = defaultdict(set)
    for row in rows:
        ticker = str(row.get("ticker") or "").strip().upper()
        cohort_date = str(row.get("cohort_date") or "")
        if ticker and cohort_date:
            groups[cohort_date].add(ticker)

    ordered = [(date, groups[date]) for date in sorted(groups)]
    sizes = [len(tickers) for _, tickers in ordered]
    pairs = []
    jaccards = []
    overlaps = []
    for (date_a, tickers_a), (date_b, tickers_b) in zip(ordered, ordered[1:]):
        intersection = len(tickers_a & tickers_b)
        union = len(tickers_a | tickers_b)
        jaccard = (intersection / union * 100.0) if union else None
        if jaccard is not None:
            jaccards.append(jaccard)
        overlaps.append(intersection)
        pairs.append({
            "from_cohort_date": date_a,
            "to_cohort_date": date_b,
            "from_n": len(tickers_a),
            "to_n": len(tickers_b),
            "overlap_n": intersection,
            "jaccard_pct": round(jaccard, 1) if jaccard is not None else None,
        })

    return {
        "cohort_count": len(ordered),
        "cohort_size": {
            "min": min(sizes) if sizes else None,
            "max": max(sizes) if sizes else None,
            "median": round(statistics.median(sizes), 1) if sizes else None,
            "range": (max(sizes) - min(sizes)) if sizes else None,
        },
        "adjacent_pair_count": len(pairs),
        "median_adjacent_jaccard_pct": (
            round(statistics.median(jaccards), 1) if jaccards else None
        ),
        "min_adjacent_jaccard_pct": round(min(jaccards), 1) if jaccards else None,
        "median_adjacent_overlap_n": (
            round(statistics.median(overlaps), 1) if overlaps else None
        ),
        "pairs": pairs,
        "interpretation": (
            "Descriptive only. Low adjacent overlap can make apparent model-performance "
            "changes partly reflect a changing universe rather than a changing model signal."
        ),
    }



def score_model_assignment_stability(rows):
    """Track whether the same tickers retain the same score model across adjacent cohorts."""
    groups = defaultdict(dict)
    for row in rows:
        ticker = str(row.get("ticker") or "").strip().upper()
        cohort_date = str(row.get("cohort_date") or "")
        model = str(row.get("score_model") or "general").strip() or "general"
        if ticker and cohort_date:
            groups[cohort_date][ticker] = model

    ordered = [(date, groups[date]) for date in sorted(groups)]
    pairs = []
    retention_pcts = []
    migrated_total = 0
    transition_counts = defaultdict(int)

    for (date_a, models_a), (date_b, models_b) in zip(ordered, ordered[1:]):
        overlap = sorted(set(models_a) & set(models_b))
        retained = 0
        migrated = 0
        pair_transitions = defaultdict(int)
        for ticker in overlap:
            model_a = models_a[ticker]
            model_b = models_b[ticker]
            if model_a == model_b:
                retained += 1
            else:
                migrated += 1
                key = (model_a, model_b)
                pair_transitions[key] += 1
                transition_counts[key] += 1

        retention_pct = (retained / len(overlap) * 100.0) if overlap else None
        if retention_pct is not None:
            retention_pcts.append(retention_pct)
        migrated_total += migrated
        pairs.append({
            "from_cohort_date": date_a,
            "to_cohort_date": date_b,
            "overlap_n": len(overlap),
            "retained_model_n": retained,
            "migrated_model_n": migrated,
            "model_retention_pct": round(retention_pct, 1) if retention_pct is not None else None,
            "transitions": [
                {"from_model": a, "to_model": b, "n": n}
                for (a, b), n in sorted(
                    pair_transitions.items(),
                    key=lambda item: (-item[1], item[0][0], item[0][1]),
                )
            ],
        })

    return {
        "cohort_count": len(ordered),
        "adjacent_pair_count": len(pairs),
        "median_adjacent_model_retention_pct": (
            round(statistics.median(retention_pcts), 1) if retention_pcts else None
        ),
        "min_adjacent_model_retention_pct": (
            round(min(retention_pcts), 1) if retention_pcts else None
        ),
        "migrated_model_assignments": migrated_total,
        "top_transitions": [
            {"from_model": a, "to_model": b, "n": n}
            for (a, b), n in sorted(
                transition_counts.items(),
                key=lambda item: (-item[1], item[0][0], item[0][1]),
            )[:10]
        ],
        "pairs": pairs,
        "interpretation": (
            "Descriptive only. Low retention means longitudinal model evidence may partly "
            "reflect score-model reassignment of the same tickers rather than signal drift."
        ),
    }

def grouped_cohort_evidence(vals, field):
    groups = defaultdict(list)
    for row in vals:
        groups[str(row.get(field) or "Unknown")].append(row)
    out = {}
    for key, rows in sorted(groups.items()):
        if len(rows) < MIN_BREAKDOWN_N:
            continue
        cohorts = cohort_summaries(rows)
        cohort_ics = [
            num(x.get("rank_information_coefficient")) for x in cohorts
            if num(x.get("rank_information_coefficient")) is not None
        ]
        cohort_spreads = [
            num(x.get("winsorized_top_minus_bottom_pct")) for x in cohorts
            if num(x.get("winsorized_top_minus_bottom_pct")) is not None
        ]
        pooled = metric_pack(rows)
        pooled.update({
            "cohort_count": len(cohorts),
            "median_cohort_rank_ic": round(statistics.median(cohort_ics), 4) if cohort_ics else None,
            "positive_ic_cohorts": sum(1 for x in cohort_ics if x > 0),
            "median_cohort_robust_spread_pct": round(statistics.median(cohort_spreads), 2) if cohort_spreads else None,
            "positive_robust_spread_cohorts": sum(1 for x in cohort_spreads if x > 0),
            "stability": cohort_stability_diagnostics(cohorts),
            "composition_stability": cohort_composition_diagnostics(rows),
            "status": validation_status(len(cohorts)),
            "cohorts": cohorts,
        })
        out[key] = pooled
    return out


def validation_status(cohort_count):
    if cohort_count < 4:
        return "collecting_evidence"
    if cohort_count < 8:
        return "early_signal"
    return "multiple_cohorts_available"


def score_v2_readiness(horizons, candidate_role="none", candidate_id=None):
    """Conservative gate for considering a production score experiment.

    This is intentionally stricter than validation_status(): having several
    observations is not evidence that a replacement is better. A v2 candidate
    should not reach production discussion until two horizons each have at
    least eight matured cohorts, adequate cohort capture, positive robust
    production diagnostics, and a prospective shadow candidate that improves
    rank IC on the same rows without worsening robust quintile separation.
    """
    qualified = []
    blockers = []
    independent_candidate = candidate_role == "candidate" and bool(candidate_id)
    for horizon in HORIZONS:
        pack = horizons.get(str(horizon)) or {}
        cohorts = int(pack.get("cohort_count") or 0)
        capture = num(pack.get("cohort_capture_pct"))
        prod_ic = num(pack.get("median_cohort_rank_ic"))
        prod_spread = num(pack.get("median_cohort_robust_spread_pct"))
        peer = pack.get("peer_shadow_comparison") or {}
        peer_cohorts = int(peer.get("cohort_count") or 0)
        prod_peer_ic = num(peer.get("median_production_cohort_rank_ic"))
        cand_ic = num(peer.get("median_peer_shadow_cohort_rank_ic"))
        prod_peer_spread = num(peer.get("median_production_cohort_robust_spread_pct"))
        cand_spread = num(peer.get("median_peer_shadow_cohort_robust_spread_pct"))

        reasons = []
        if not independent_candidate:
            reasons.append("no_independent_score_candidate")
        if cohorts < 8:
            reasons.append("fewer_than_8_matured_cohorts")
        if capture is None or capture < 80:
            reasons.append("cohort_capture_below_80pct")
        if prod_ic is None or prod_ic <= 0:
            reasons.append("production_median_rank_ic_not_positive")
        if prod_spread is None or prod_spread <= 0:
            reasons.append("production_median_spread_not_positive")
        if peer_cohorts < 8:
            reasons.append("shadow_has_fewer_than_8_cohorts")
        if prod_peer_ic is None or cand_ic is None or cand_ic <= prod_peer_ic:
            reasons.append("shadow_rank_ic_not_better")
        if prod_peer_spread is None or cand_spread is None or cand_spread < prod_peer_spread:
            reasons.append("shadow_spread_worse_or_unavailable")

        if reasons:
            blockers.append({"horizon_days": horizon, "reasons": reasons})
        else:
            qualified.append(horizon)

    ready = len(qualified) >= 2
    return {
        "status": "candidate_review_allowed" if ready else "production_change_deferred",
        "production_weights_frozen": not ready,
        "qualified_horizons": qualified,
        "required_qualified_horizons": 2,
        "candidate_role": candidate_role,
        "candidate_id": candidate_id if independent_candidate else None,
        "independent_candidate_active": independent_candidate,
        "blockers": blockers,
        "rule": (
            "A genuinely independent Score v2 candidate may enter production review only after at least two horizons "
            "independently satisfy the prospective evidence gate. A production-parity reconstruction cannot qualify. "
            "Passing permits review, not deployment."
        ),
    }


def peer_shadow_comparison(vals, role="legacy_candidate", candidate_active=False, candidate_id=None):
    peer_vals = [x for x in vals if num(x.get("peer_shadow_score")) is not None]
    production = metric_pack(peer_vals, "score")
    candidate = metric_pack(peer_vals, "peer_shadow_score")

    groups = defaultdict(list)
    for row in peer_vals:
        groups[str(row.get("cohort_date"))].append(row)

    cohorts = []
    candidate_ics = []
    production_ics = []
    candidate_spreads = []
    production_spreads = []
    candidate_robust_spreads = []
    production_robust_spreads = []
    for date, rows in sorted(groups.items()):
        prod = metric_pack(rows, "score")
        peer = metric_pack(rows, "peer_shadow_score")
        p_ic = num(prod.get("rank_information_coefficient"))
        c_ic = num(peer.get("rank_information_coefficient"))
        p_spread = num(prod.get("top_minus_bottom_pct"))
        c_spread = num(peer.get("top_minus_bottom_pct"))
        p_robust_spread = num(prod.get("winsorized_top_minus_bottom_pct"))
        c_robust_spread = num(peer.get("winsorized_top_minus_bottom_pct"))
        if p_ic is not None:
            production_ics.append(p_ic)
        if c_ic is not None:
            candidate_ics.append(c_ic)
        if p_spread is not None:
            production_spreads.append(p_spread)
        if c_spread is not None:
            candidate_spreads.append(c_spread)
        if p_robust_spread is not None:
            production_robust_spreads.append(p_robust_spread)
        if c_robust_spread is not None:
            candidate_robust_spreads.append(c_robust_spread)
        cohorts.append({
            "cohort_date": date,
            "n": len(rows),
            "production": prod,
            "peer_shadow": peer,
            "rank_ic_delta": round(c_ic - p_ic, 4) if c_ic is not None and p_ic is not None else None,
            "top_minus_bottom_delta_pct": round(c_spread - p_spread, 2) if c_spread is not None and p_spread is not None else None,
            "robust_spread_delta_pct": round(c_robust_spread - p_robust_spread, 2) if c_robust_spread is not None and p_robust_spread is not None else None,
        })

    return {
        "role": role,
        "candidate_active": bool(candidate_active and role == "candidate"),
        "candidate_id": candidate_id if candidate_active and role == "candidate" else None,
        "eligible_for_candidate_readiness": bool(candidate_active and role == "candidate" and candidate_id),
        "eligible_n": len(peer_vals),
        "cohort_count": len(cohorts),
        "production_same_subset": production,
        "peer_shadow": candidate,
        "median_production_cohort_rank_ic": round(statistics.median(production_ics), 4) if production_ics else None,
        "median_peer_shadow_cohort_rank_ic": round(statistics.median(candidate_ics), 4) if candidate_ics else None,
        "median_production_cohort_top_minus_bottom_pct": round(statistics.median(production_spreads), 2) if production_spreads else None,
        "median_peer_shadow_cohort_top_minus_bottom_pct": round(statistics.median(candidate_spreads), 2) if candidate_spreads else None,
        "median_production_cohort_robust_spread_pct": round(statistics.median(production_robust_spreads), 2) if production_robust_spreads else None,
        "median_peer_shadow_cohort_robust_spread_pct": round(statistics.median(candidate_robust_spreads), 2) if candidate_robust_spreads else None,
        "positive_peer_shadow_ic_cohorts": sum(1 for x in candidate_ics if x > 0),
        "positive_peer_shadow_spread_cohorts": sum(1 for x in candidate_spreads if x > 0),
        "cohorts": cohorts,
    }


def summarize_horizon(vals, expected_matured_cohorts=0, shadow_role="legacy_candidate", shadow_candidate_active=False, shadow_candidate_id=None):
    cohorts = cohort_summaries(vals)
    pack = metric_pack(vals)
    pack["peer_shadow_comparison"] = peer_shadow_comparison(
        vals,
        role=shadow_role,
        candidate_active=shadow_candidate_active,
        candidate_id=shadow_candidate_id,
    )
    cohort_ics = [num(x.get("rank_information_coefficient")) for x in cohorts]
    cohort_ics = [x for x in cohort_ics if x is not None]
    cohort_spreads = [num(x.get("top_minus_bottom_pct")) for x in cohorts]
    cohort_spreads = [x for x in cohort_spreads if x is not None]
    cohort_robust_spreads = [num(x.get("winsorized_top_minus_bottom_pct")) for x in cohorts]
    cohort_robust_spreads = [x for x in cohort_robust_spreads if x is not None]
    pack.update({
        "cohort_count": len(cohorts),
        "expected_matured_cohorts": expected_matured_cohorts,
        "cohort_capture_pct": round(len(cohorts) / expected_matured_cohorts * 100, 1) if expected_matured_cohorts else None,
        "median_cohort_rank_ic": round(statistics.median(cohort_ics), 4) if cohort_ics else None,
        "positive_ic_cohorts": sum(1 for x in cohort_ics if x > 0),
        "median_cohort_top_minus_bottom_pct": round(statistics.median(cohort_spreads), 2) if cohort_spreads else None,
        "positive_spread_cohorts": sum(1 for x in cohort_spreads if x > 0),
        "median_cohort_robust_spread_pct": round(statistics.median(cohort_robust_spreads), 2) if cohort_robust_spreads else None,
        "positive_robust_spread_cohorts": sum(1 for x in cohort_robust_spreads if x > 0),
        "factor_rank_information_coefficient": factor_ics(vals),
        "score_model_assignment_stability": score_model_assignment_stability(vals),
        "by_score_model": grouped_cohort_evidence(vals, "score_model"),
        "by_sector": grouped_breakdown(vals, "sector"),
        "cohorts": cohorts,
        "status": validation_status(len(cohorts)),
    })
    return pack


def expected_matured_count(today, snapshots, horizon):
    count = 0
    for snap in snapshots:
        try:
            age = (today - dt.date.fromisoformat(snap["date"])).days
        except Exception:
            continue
        if age >= horizon:
            count += 1
    return count


def maturity_dates(today, snapshots, horizon):
    dates = []
    for snap in snapshots:
        try:
            dates.append(dt.date.fromisoformat(snap["date"]))
        except Exception:
            continue
    if not dates:
        return None, None
    maturity = sorted(d + dt.timedelta(days=horizon) for d in dates)
    first = maturity[0]
    pending = [d for d in maturity if d > today]
    return first, (pending[0] if pending else None)



def evaluate_report_freshness(report, now=None):
    """Machine-check whether a validation report is still safe to interpret as current."""
    now = now or dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=dt.timezone.utc)
    reasons = []
    if int(report.get("schema_version") or 0) != REPORT_SCHEMA_VERSION:
        reasons.append("schema_version_mismatch")
    if str(report.get("generator_version") or "") != REPORT_GENERATOR_VERSION:
        reasons.append("generator_version_mismatch")
    freshness = report.get("freshness") if isinstance(report.get("freshness"), dict) else {}
    try:
        valid_through = dt.datetime.fromisoformat(str(freshness.get("valid_through") or ""))
        if valid_through.tzinfo is None:
            valid_through = valid_through.replace(tzinfo=dt.timezone.utc)
        if now > valid_through:
            reasons.append("report_expired")
    except Exception:
        reasons.append("missing_or_invalid_valid_through")
    return {
        "is_current": not reasons,
        "reasons": reasons,
        "expected_schema_version": REPORT_SCHEMA_VERSION,
        "expected_generator_version": REPORT_GENERATOR_VERSION,
    }

def validate_report_contract(report, now=None):
    """Validate the full published-report contract from one canonical implementation."""
    freshness = evaluate_report_freshness(report, now=now)
    reasons = list(freshness["reasons"])
    horizons = report.get("horizons") if isinstance(report.get("horizons"), dict) else {}
    if not horizons:
        reasons.append("missing_horizons")
    else:
        for horizon_days, pack in horizons.items():
            models = (pack or {}).get("by_score_model") if isinstance(pack, dict) else None
            models = models if isinstance(models, dict) else {}
            pack_n = int((pack or {}).get("n") or 0) if isinstance(pack, dict) else 0
            pack_cohorts = int((pack or {}).get("cohort_count") or 0) if isinstance(pack, dict) else 0
            if pack_cohorts >= 2 and "score_model_assignment_stability" not in (pack or {}):
                reasons.append(f"missing_score_model_assignment_stability:{horizon_days}")
            if pack_cohorts > 0 and pack_n >= MIN_BREAKDOWN_N:
                if not models:
                    reasons.append(f"missing_score_model_breakdown:{horizon_days}")
                else:
                    captured_n = sum(
                        int((model_pack or {}).get("n") or 0)
                        for model_pack in models.values()
                        if isinstance(model_pack, dict)
                    )
                    capture_pct = (captured_n / pack_n * 100.0) if pack_n else 0.0
                    if capture_pct < 98.0:
                        reasons.append(
                            f"score_model_breakdown_capture_below_98pct:{horizon_days}:{capture_pct:.1f}"
                        )
            for model_name, model_pack in models.items():
                if not isinstance(model_pack, dict):
                    reasons.append(f"invalid_model_pack:{horizon_days}:{model_name}")
                    continue
                if "stability" not in model_pack:
                    reasons.append(f"missing_stability:{horizon_days}:{model_name}")
                if "composition_stability" not in model_pack:
                    reasons.append(f"missing_composition_stability:{horizon_days}:{model_name}")
    return {
        "is_valid": not reasons,
        "reasons": reasons,
        "freshness": freshness,
        "generator_version": report.get("generator_version"),
        "schema_version": report.get("schema_version"),
    }

def main():
    today = dt.date.today()
    rows = current_rows()
    price_rows = current_price_rows()
    shadow_state = peer_shadow_state()
    shadow_scores = shadow_state["scores"]
    history = load_json(HISTORY, {"schema_version": 3, "snapshots": [], "outcomes": []})
    snapshots = history.setdefault("snapshots", [])
    outcomes = history.setdefault("outcomes", [])

    latest_date = None
    if snapshots:
        try:
            latest_date = max(dt.date.fromisoformat(s["date"]) for s in snapshots)
        except Exception:
            latest_date = None

    latest_snapshot = None
    if latest_date is not None:
        latest_snapshot = next(
            (s for s in reversed(snapshots) if str(s.get("date") or "") == latest_date.isoformat()),
            None,
        )
    latest_has_peer_shadow = bool(
        latest_snapshot
        and any(
            num(obs.get("peer_shadow_score")) is not None
            for obs in (latest_snapshot.get("observations") or {}).values()
            if isinstance(obs, dict)
        )
    )
    needs_peer_shadow_baseline = bool(shadow_scores) and not latest_has_peer_shadow

    if latest_date is None or (today - latest_date).days >= 7 or (
        needs_peer_shadow_baseline and latest_date != today
    ):
        snapshots.append(make_snapshot(today, rows, shadow_scores, price_rows))
    elif needs_peer_shadow_baseline and latest_date == today and latest_snapshot:
        # Same-day upgrade is still prospective: attach only the candidate that
        # exists now to today's already-recorded observations, never to older dates.
        for ticker, observation in (latest_snapshot.get("observations") or {}).items():
            if isinstance(observation, dict):
                observation["peer_shadow_score"] = num(shadow_scores.get(ticker))

    cutoff = today - dt.timedelta(days=RETENTION_DAYS)
    snapshots[:] = [
        s for s in snapshots
        if isinstance(s, dict) and dt.date.fromisoformat(s["date"]) >= cutoff
    ]
    outcomes[:] = [
        x for x in outcomes
        if isinstance(x, dict) and dt.date.fromisoformat(str(x.get("cohort_date"))) >= cutoff
    ]

    added = materialise_outcomes(today, snapshots, price_rows, outcomes)
    repaired = repair_persisted_split_outcomes(outcomes, snapshots)

    report_horizons = {}
    for horizon in HORIZONS:
        vals = [
            x for x in outcomes
            if int(x.get("horizon_days") or 0) == horizon
            and x.get("validation_eligible") is not False
        ]
        expected = expected_matured_count(today, snapshots, horizon)
        summary = summarize_horizon(
            vals,
            expected,
            shadow_role=shadow_state["role"],
            shadow_candidate_active=shadow_state["candidate_active"],
            shadow_candidate_id=shadow_state["candidate_id"],
        )
        first_maturity, next_maturity = maturity_dates(today, snapshots, horizon)
        summary["first_possible_maturity_date"] = first_maturity.isoformat() if first_maturity else None
        summary["next_pending_maturity_date"] = next_maturity.isoformat() if next_maturity else None
        report_horizons[str(horizon)] = summary

    history["schema_version"] = 4
    history["updated_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    history["snapshot_count"] = len(snapshots)
    history["outcome_count"] = len(outcomes)
    HISTORY.write_text(
        json.dumps(history, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n",
        encoding="utf-8",
    )

    report_generated_at = dt.datetime.now(dt.timezone.utc)
    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "generator_version": REPORT_GENERATOR_VERSION,
        "generated_at": report_generated_at.isoformat(),
        "freshness": {
            "status": "current_at_generation",
            "as_of_date": today.isoformat(),
            "valid_through": (report_generated_at + dt.timedelta(hours=REPORT_VALIDITY_HOURS)).isoformat(),
            "validity_hours": REPORT_VALIDITY_HOURS,
            "latest_snapshot_date": latest_date.isoformat() if latest_date else None,
            "stale_if": "expired valid_through or generator/schema version differs from the current validator",
        },
        "methodology": "prospective weekly cohorts; persistent realised outcomes; no reconstructed historical scores",
        "horizons_days": list(HORIZONS),
        "snapshots_available": len(snapshots),
        "realised_outcomes": len(outcomes),
        "new_outcomes_this_run": added,
        "repaired_corporate_action_outcomes_this_run": repaired,
        "horizons": report_horizons,
        "score_v2_readiness": score_v2_readiness(
            report_horizons,
            candidate_role=shadow_state["role"] if shadow_state["candidate_active"] else "none",
            candidate_id=shadow_state["candidate_id"],
        ),
        "interpretation": {
            "rank_ic": "Spearman correlation between the score known at cohort date and realised forward return.",
            "top_minus_bottom": "Raw mean return spread between highest and lowest score quintiles; retain it for transparency but inspect robust companions when tails are extreme.",
            "robust_quintile_spreads": "Median and 5% winsorized-mean top-minus-bottom spreads are reported alongside the raw mean. They are diagnostics, not replacements chosen after seeing outcomes.",
            "corporate_actions": "Known splits/reverse splits are normalized onto the end-date share-price basis. Stock distributions/spin-offs add the distributed child value when an end-date reference price is available; unresolved corporate-action outcomes are retained for auditability but excluded from validation metrics.",
            "cohort_statistics": "Median cohort IC/spread is preferred to one pooled number because weekly cross-sections overlap. Score-model breakdowns include their own cohort_count, medians and positive-cohort counts; model status is never inferred from pooled n alone.",
            "factor_ics": "Diagnostic only. Do not change factor weights from a small sample or one market regime.",
            "peer_shadow": "The current peer shadow is a production-parity reconstruction, not an independent challenger. Historical peer_shadow_score values are retained for lineage/parity diagnostics but cannot unlock Score v2 readiness unless a future shadow is explicitly marked role=candidate with a non-empty candidate_id.",
        },
        "decision_rule": (
            "Do not optimize production weights from pooled n alone. Require multiple matured weekly cohorts, "
            "preferably at least 8 per horizon and evidence across at least two horizons, with stable positive "
            "median cohort rank IC and top-minus-bottom spread across score models/sectors."
        ),
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(
        f"Forward validation: snapshots={len(snapshots)} outcomes={len(outcomes)} "
        f"new={added} statuses={{h: report_horizons[str(h)]['status'] for h in HORIZONS}}"
    )


if __name__ == "__main__":
    main()
