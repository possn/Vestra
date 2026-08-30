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
HORIZONS = (28, 84, 168)
MAX_HORIZON_LATENESS_DAYS = 10
RETENTION_DAYS = 800
MIN_CORRELATION_N = 20
MIN_BREAKDOWN_N = 30
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


def make_snapshot(today, rows):
    observations = {}
    for ticker, r in rows.items():
        observations[ticker] = {
            "price": num(r.get("current_price")),
            "sector": str(r.get("sector") or "Unknown"),
            "score_model": str(r.get("score_model") or "general"),
            "confidence_score": num(r.get("confidence_score")),
            "risk_gate": str(r.get("risk_gate") or "clear"),
            **{field: num(r.get(field)) for field in FIELDS},
        }
    return {"date": today.isoformat(), "observations": observations}


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
                realised = (p1 / p0 - 1.0) * 100.0
                item = {
                    "cohort_date": snap["date"],
                    "evaluated_date": today.isoformat(),
                    "actual_days": age,
                    "horizon_days": horizon,
                    "ticker": ticker,
                    "start_price": round(p0, 8),
                    "end_price": round(p1, 8),
                    "return_pct": round(realised, 6),
                    "sector": old.get("sector") or "Unknown",
                    "score_model": old.get("score_model") or "general",
                    "confidence_score": num(old.get("confidence_score")),
                    "risk_gate": old.get("risk_gate") or "clear",
                    **{field: num(old.get(field)) for field in FIELDS},
                }
                outcomes.append(item)
                existing.add(key)
                added += 1
    return added


def mean(values):
    vals = [num(v) for v in values]
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals) if vals else None


def quintile_metrics(vals):
    ordered = sorted(vals, key=lambda x: num(x.get("score")) if num(x.get("score")) is not None else -1e9, reverse=True)
    if not ordered:
        return None, None, None
    q = max(1, len(ordered) // 5)
    top = ordered[:q]
    bottom = ordered[-q:]
    top_mean = mean([x.get("return_pct") for x in top])
    bottom_mean = mean([x.get("return_pct") for x in bottom])
    spread = top_mean - bottom_mean if top_mean is not None and bottom_mean is not None else None
    return top_mean, bottom_mean, spread


def metric_pack(vals):
    ic = spearman([(x.get("score"), x.get("return_pct")) for x in vals])
    top_mean, bottom_mean, spread = quintile_metrics(vals)
    return {
        "n": len(vals),
        "rank_information_coefficient": round(ic, 4) if ic is not None else None,
        "top_quintile_mean_return_pct": round(top_mean, 2) if top_mean is not None else None,
        "bottom_quintile_mean_return_pct": round(bottom_mean, 2) if bottom_mean is not None else None,
        "top_minus_bottom_pct": round(spread, 2) if spread is not None else None,
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


def validation_status(cohort_count):
    if cohort_count < 4:
        return "collecting_evidence"
    if cohort_count < 8:
        return "early_signal"
    return "multiple_cohorts_available"


def summarize_horizon(vals, expected_matured_cohorts=0):
    cohorts = cohort_summaries(vals)
    pack = metric_pack(vals)
    cohort_ics = [num(x.get("rank_information_coefficient")) for x in cohorts]
    cohort_ics = [x for x in cohort_ics if x is not None]
    cohort_spreads = [num(x.get("top_minus_bottom_pct")) for x in cohorts]
    cohort_spreads = [x for x in cohort_spreads if x is not None]
    pack.update({
        "cohort_count": len(cohorts),
        "expected_matured_cohorts": expected_matured_cohorts,
        "cohort_capture_pct": round(len(cohorts) / expected_matured_cohorts * 100, 1) if expected_matured_cohorts else None,
        "median_cohort_rank_ic": round(statistics.median(cohort_ics), 4) if cohort_ics else None,
        "positive_ic_cohorts": sum(1 for x in cohort_ics if x > 0),
        "median_cohort_top_minus_bottom_pct": round(statistics.median(cohort_spreads), 2) if cohort_spreads else None,
        "positive_spread_cohorts": sum(1 for x in cohort_spreads if x > 0),
        "factor_rank_information_coefficient": factor_ics(vals),
        "by_score_model": grouped_breakdown(vals, "score_model"),
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


def main():
    today = dt.date.today()
    rows = current_rows()
    history = load_json(HISTORY, {"schema_version": 2, "snapshots": [], "outcomes": []})
    snapshots = history.setdefault("snapshots", [])
    outcomes = history.setdefault("outcomes", [])

    latest_date = None
    if snapshots:
        try:
            latest_date = max(dt.date.fromisoformat(s["date"]) for s in snapshots)
        except Exception:
            latest_date = None

    if latest_date is None or (today - latest_date).days >= 7:
        snapshots.append(make_snapshot(today, rows))

    cutoff = today - dt.timedelta(days=RETENTION_DAYS)
    snapshots[:] = [
        s for s in snapshots
        if isinstance(s, dict) and dt.date.fromisoformat(s["date"]) >= cutoff
    ]
    outcomes[:] = [
        x for x in outcomes
        if isinstance(x, dict) and dt.date.fromisoformat(str(x.get("cohort_date"))) >= cutoff
    ]

    added = materialise_outcomes(today, snapshots, rows, outcomes)

    report_horizons = {}
    for horizon in HORIZONS:
        vals = [x for x in outcomes if int(x.get("horizon_days") or 0) == horizon]
        expected = expected_matured_count(today, snapshots, horizon)
        summary = summarize_horizon(vals, expected)
        first_maturity, next_maturity = maturity_dates(today, snapshots, horizon)
        summary["first_possible_maturity_date"] = first_maturity.isoformat() if first_maturity else None
        summary["next_pending_maturity_date"] = next_maturity.isoformat() if next_maturity else None
        report_horizons[str(horizon)] = summary

    history["schema_version"] = 2
    history["updated_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    history["snapshot_count"] = len(snapshots)
    history["outcome_count"] = len(outcomes)
    HISTORY.write_text(
        json.dumps(history, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n",
        encoding="utf-8",
    )

    report = {
        "schema_version": 2,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "methodology": "prospective weekly cohorts; persistent realised outcomes; no reconstructed historical scores",
        "horizons_days": list(HORIZONS),
        "snapshots_available": len(snapshots),
        "realised_outcomes": len(outcomes),
        "new_outcomes_this_run": added,
        "horizons": report_horizons,
        "interpretation": {
            "rank_ic": "Spearman correlation between the score known at cohort date and realised forward return.",
            "top_minus_bottom": "Mean return of the highest score quintile minus the lowest score quintile.",
            "cohort_statistics": "Median cohort IC/spread is preferred to one pooled number because weekly cross-sections overlap.",
            "factor_ics": "Diagnostic only. Do not change factor weights from a small sample or one market regime.",
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
