"""Append-only, content-addressed forecast capture.

Capture requires an externally provided trusted UTC observation time. Git history
and stored hashes provide audit evidence, not an independent timestamp authority.
Forecast input must come from a live model at capture time, never reconstructed.
"""
import hashlib
import json
from pathlib import Path
from scripts.model_evidence_ledger import parse_time

FIELDS = ("model_id", "model_version", "prediction_id", "ticker",
          "issued_at", "horizon_end", "probability_up", "split")


def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def append_forecast(path, forecast, observed_at):
    observed = parse_time(observed_at)
    if not isinstance(forecast, dict) or set(forecast) != set(FIELDS):
        raise ValueError("unexpected forecast fields")
    if not all(isinstance(forecast[k], str) and forecast[k].strip()
               for k in ("model_id", "model_version", "prediction_id", "ticker")):
        raise ValueError("identity missing")
    issued = parse_time(forecast["issued_at"])
    end = parse_time(forecast["horizon_end"])
    if not (issued <= observed < end):
        raise ValueError("forecast not live at capture time")
    if forecast["split"] != "out_of_sample":
        raise ValueError("requires out-of-sample")
    p = forecast["probability_up"]
    if type(p) not in (int, float) or not 0 <= p <= 1:
        raise ValueError("invalid probability")
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    previous = "0" * 64
    seen = set()
    if target.exists():
        for line in target.read_text(encoding="utf-8").splitlines():
            event = json.loads(line)
            body = {k: event[k] for k in ("forecast", "captured_at", "previous_hash")}
            digest = hashlib.sha256(canonical(body).encode()).hexdigest()
            if digest != event.get("hash") or event["previous_hash"] != previous:
                raise ValueError("ledger integrity failure")
            previous = digest
            identity = tuple(event["forecast"][k] for k in ("model_id", "model_version", "prediction_id"))
            if identity in seen:
                raise ValueError("existing duplicate")
            seen.add(identity)
    identity = tuple(forecast[k] for k in ("model_id", "model_version", "prediction_id"))
    if identity in seen:
        raise ValueError("duplicate prediction")
    body = {"forecast": forecast, "captured_at": observed.isoformat(), "previous_hash": previous}
    event = dict(body, hash=hashlib.sha256(canonical(body).encode()).hexdigest())
    with target.open("a", encoding="utf-8") as handle:
        handle.write(canonical(event) + "\n")
    return event
