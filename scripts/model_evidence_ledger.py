"""Evidence ledger: evaluate only matured, point-in-time predictions.

Input is a list of records (never current quotes masquerading as historical outcomes).
No eligible observations means unavailable, not 0% accuracy.
"""
from datetime import datetime, timezone
import json
import sys


def parse_time(value):
    if not isinstance(value, str):
        raise ValueError("timestamp required")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timezone required")
    return parsed.astimezone(timezone.utc)


def evaluate(records, as_of):
    now = parse_time(as_of)
    eligible = []
    rejected = {}
    for item in records:
        try:
            if not isinstance(item, dict):
                raise ValueError("malformed")
            if not all(isinstance(item.get(k), str) and item[k].strip()
                       for k in ("model_id", "ticker", "prediction_id", "model_version")):
                raise ValueError("identity_missing")
            issued = parse_time(item["issued_at"])
            horizon = parse_time(item["horizon_end"])
            observed = parse_time(item["outcome_observed_at"])
            if not (issued < horizon <= observed <= now):
                raise ValueError("non_point_in_time")
            probability = item["probability_up"]
            outcome = item["realized_up"]
            if type(probability) not in (float, int) or not 0 <= probability <= 1:
                raise ValueError("invalid_probability")
            if type(outcome) is not bool:
                raise ValueError("invalid_outcome")
            if item.get("split") != "out_of_sample":
                raise ValueError("not_out_of_sample")
            eligible.append((item["model_id"], float(probability), int(outcome)))
        except (ValueError, KeyError, TypeError) as exc:
            reason = str(exc) if isinstance(exc, ValueError) and str(exc) else "malformed"
            rejected[reason] = rejected.get(reason, 0) + 1
    results = {}
    for model_id in sorted(set(row[0] for row in eligible)):
        rows = [(p, y) for m, p, y in eligible if m == model_id]
        count = len(rows)
        results[model_id] = {
            "status": "observed_insufficient_sample" if count < 30 else "observed",
            "n": count,
            "brier": round(sum((p-y)**2 for p, y in rows)/count, 6),
            "base_rate": round(sum(y for _, y in rows)/count, 6),
            "mean_predicted": round(sum(p for p, _ in rows)/count, 6),
            "disclaimer": "Descriptive only; does not establish causal alpha or live performance",
        }
    return {"schema_version": 1, "as_of": now.isoformat(), "models": results,
            "eligible_count": len(eligible), "rejected": rejected,
            "status": "observed" if eligible else "unavailable"}


if __name__ == "__main__":
    payload = json.load(sys.stdin)
    print(json.dumps(evaluate(payload["records"], payload["as_of"]), ensure_ascii=False, indent=2))
