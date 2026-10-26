#!/usr/bin/env python3
"""Prospective shadow signal journal; research-only, no trading or probability claims.

Records are append-only JSONL with a hash chain. A hash chain detects editing
only when anchored independently: it is not proof of vendor data authenticity.
The ingestion clock is taken from the runner, not a user-supplied timestamp.
"""
from __future__ import annotations
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path

REQUIRED = ("issuer_id", "signal_session", "model_version", "rule_id",
            "source", "source_available_at_utc", "features_sha256")


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False)


def _timestamp(value):
    if not isinstance(value, str):
        raise ValueError("invalid timestamp")
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("naive timestamp")
    return dt.astimezone(timezone.utc)


def validate_signal(signal, *, capture_at_utc):
    if not isinstance(signal, dict) or any(x not in signal for x in REQUIRED):
        raise ValueError("missing signal fields")
    for key in REQUIRED:
        if not isinstance(signal[key], str) or not signal[key].strip():
            raise ValueError("invalid signal field: " + key)
    digest = signal["features_sha256"]
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError("invalid feature hash")
    capture = _timestamp(capture_at_utc)
    available = _timestamp(signal["source_available_at_utc"])
    if available > capture:
        raise ValueError("future source")
    session = datetime.strptime(signal["signal_session"], "%Y-%m-%d").date()
    if session > capture.date():
        raise ValueError("future signal session")
    if any(key not in REQUIRED for key in signal):
        raise ValueError("unexpected nonfrozen fields")
    return True


def append_signal(journal_path, signal, *, now=None):
    """Append once by event identity; rejects conflicting replays and broken chains.

    Caller must invoke on a single-writer runner with a durable journal. External
    archival/timestamp anchoring is required for tamper resistance. Do not use
    this helper concurrently or as a retrospective historical import.
    """
    capture = now or datetime.now(timezone.utc)
    if capture.tzinfo is None:
        raise ValueError("naive capture clock")
    capture_iso = capture.astimezone(timezone.utc).isoformat()
    validate_signal(signal, capture_at_utc=capture_iso)
    path = Path(journal_path)
    if path.exists():
        lines = [json.loads(v) for v in path.read_text(encoding="utf-8").splitlines() if v.strip()]
    else:
        lines = []
    previous = "0" * 64
    identities = {}
    for record in lines:
        payload = {"capture_at_utc": record["capture_at_utc"], "signal": record["signal"],
                   "previous_sha256": record["previous_sha256"]}
        if record["previous_sha256"] != previous or record["record_sha256"] != sha256(
                canonical(payload).encode("utf-8")).hexdigest():
            raise ValueError("broken journal hash chain")
        previous = record["record_sha256"]
        identity = tuple(record["signal"][field] for field in ("issuer_id", "signal_session",
                                                                "model_version", "rule_id"))
        identities[identity] = record["signal"]
    key = tuple(signal[field] for field in ("issuer_id", "signal_session", "model_version", "rule_id"))
    if key in identities:
        if identities[key] != signal:
            raise ValueError("conflicting replay of already journalled signal")
        return {"status": "ALREADY_RECORDED", "record_sha256": previous}
    payload = {"capture_at_utc": capture_iso, "signal": dict(signal),
               "previous_sha256": previous}
    digest = sha256(canonical(payload).encode("utf-8")).hexdigest()
    record = dict(payload, record_sha256=digest)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(canonical(record) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    return {"status": "RECORDED_UNVALIDATED_SIGNAL", "record_sha256": digest}
