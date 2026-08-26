"""Prospective validation tracker for Vestra scores.

This deliberately avoids retrofitting today's score onto historical prices. Once per
week it stores the score/dimensions actually known at that time. Later runs match the
same ticker to a current price and calculate realised 4/12/24-week returns. This is
out-of-sample evidence for future score-weight decisions.
"""
from __future__ import annotations

import datetime as dt
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "data" / "stocks-index.json"
HISTORY = ROOT / "data" / "score_validation_history.json"
REPORT = ROOT / "data" / "score_validation_report.json"
HORIZONS = (28, 84, 168)
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
    if len(a) < 20 or len(a) != len(b):
        return None
    am = sum(a) / len(a); bm = sum(b) / len(b)
    cov = sum((x-am)*(y-bm) for x,y in zip(a,b))
    va = sum((x-am)**2 for x in a); vb = sum((y-bm)**2 for y in b)
    if va <= 0 or vb <= 0:
        return None
    return cov / math.sqrt(va*vb)


def spearman(pairs):
    clean = [(num(a), num(b)) for a,b in pairs]
    clean = [(a,b) for a,b in clean if a is not None and b is not None]
    if len(clean) < 20:
        return None
    return pearson(rank([a for a,_ in clean]), rank([b for _,b in clean]))


def load_json(path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
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
        if str(r.get("quote_type") or "").upper() in {"ETF","CRYPTO","FUND","MUTUALFUND"}:
            continue
        if str(r.get("pipeline_status") or "") in {"equity_catalog_only","equity_carried_forward"}:
            continue
        out[ticker] = r
    return out


def main():
    today = dt.date.today()
    rows = current_rows()
    history = load_json(HISTORY, {"schema_version": 1, "snapshots": []})
    snapshots = history.setdefault("snapshots", [])

    latest_date = None
    if snapshots:
        try: latest_date = max(dt.date.fromisoformat(s["date"]) for s in snapshots)
        except Exception: latest_date = None

    # Weekly cadence prevents repository bloat while giving enough independent
    # cross-sections for 4/12/24-week validation.
    if latest_date is None or (today - latest_date).days >= 7:
        observations = {}
        for ticker, r in rows.items():
            observations[ticker] = {
                "price": num(r.get("current_price")),
                "sector": str(r.get("sector") or "Unknown"),
                "score_model": str(r.get("score_model") or "general"),
                **{field: num(r.get(field)) for field in FIELDS},
            }
        snapshots.append({"date": today.isoformat(), "observations": observations})

    # Retain a little over two years; enough for multiple 24-week cohorts.
    cutoff = today - dt.timedelta(days=800)
    snapshots[:] = [s for s in snapshots if dt.date.fromisoformat(s["date"]) >= cutoff]

    evaluations = {str(h): [] for h in HORIZONS}
    for snap in snapshots:
        snap_date = dt.date.fromisoformat(snap["date"])
        age = (today - snap_date).days
        obs = snap.get("observations") or {}
        for horizon in HORIZONS:
            # Evaluate each cohort once it is within one weekly interval of target.
            if not (horizon <= age < horizon + 7):
                continue
            for ticker, old in obs.items():
                now = rows.get(ticker)
                if not now:
                    continue
                p0 = num(old.get("price")); p1 = num(now.get("current_price"))
                score = num(old.get("score"))
                if p0 is None or p1 is None or p0 <= 0 or score is None:
                    continue
                evaluations[str(horizon)].append({
                    "ticker": ticker,
                    "score": score,
                    "return_pct": (p1 / p0 - 1) * 100,
                    "sector": old.get("sector"),
                    "score_model": old.get("score_model"),
                    "cohort_date": snap["date"],
                })

    report_horizons = {}
    for horizon, vals in evaluations.items():
        ic = spearman([(x["score"], x["return_pct"]) for x in vals])
        ordered = sorted(vals, key=lambda x: x["score"], reverse=True)
        q = max(1, len(ordered)//5) if ordered else 0
        top = ordered[:q]; bottom = ordered[-q:] if q else []
        top_mean = sum(x["return_pct"] for x in top)/len(top) if top else None
        bottom_mean = sum(x["return_pct"] for x in bottom)/len(bottom) if bottom else None
        report_horizons[horizon] = {
            "n": len(vals),
            "rank_information_coefficient": round(ic, 4) if ic is not None else None,
            "top_quintile_mean_return_pct": round(top_mean, 2) if top_mean is not None else None,
            "bottom_quintile_mean_return_pct": round(bottom_mean, 2) if bottom_mean is not None else None,
            "top_minus_bottom_pct": round(top_mean-bottom_mean, 2) if top_mean is not None and bottom_mean is not None else None,
            "status": "enough_observations" if len(vals) >= 100 else "collecting_evidence",
        }

    history["updated_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    history["snapshot_count"] = len(snapshots)
    HISTORY.write_text(json.dumps(history, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n", encoding="utf-8")

    report = {
        "schema_version": 1,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "methodology": "prospective weekly cohorts; no reconstructed historical scores",
        "horizons_days": list(HORIZONS),
        "snapshots_available": len(snapshots),
        "horizons": report_horizons,
        "decision_rule": "Do not optimize production weights until multiple independent cohorts exist; prefer stable positive rank IC and top-minus-bottom spread across horizons and sectors.",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Forward validation: {len(snapshots)} weekly snapshots; horizons={report_horizons}")


if __name__ == "__main__":
    main()
