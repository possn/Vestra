#!/usr/bin/env python3
"""Offline PIT dataset admission gate; never promotes an unverified sample to research-ready."""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

REQUIRED=("dataset_id","vendor","license","source_uri","raw_sha256","collected_at_utc",
          "available_at_utc","universe_asof_method","delistings_included",
          "corporate_actions_method","price_adjustment","trading_calendar",
          "currency_units","sector_asof_method","benchmark_asof_method",
          "missing_sessions_audited","historical_span_start","historical_span_end")


def validate_manifest(manifest: dict, raw: bytes, *, evaluation_utc: str) -> dict:
    """Fail closed; admission != statistical validation or license verification."""
    failures=[]
    if not isinstance(manifest,dict):
        return {"admitted":False,"failures":["invalid_manifest"]}
    for name in REQUIRED:
        if name not in manifest or manifest[name] is None or manifest[name]=="":
            failures.append("missing_"+name)
    try:
        now=datetime.fromisoformat(evaluation_utc.replace("Z","+00:00"))
        available=datetime.fromisoformat(manifest["available_at_utc"].replace("Z","+00:00"))
        collected=datetime.fromisoformat(manifest["collected_at_utc"].replace("Z","+00:00"))
        if any(x.tzinfo is None for x in (now,available,collected)):
            failures.append("naive_timestamp")
        elif available>now or collected>now:
            failures.append("future_availability")
    except (KeyError,ValueError,TypeError,AttributeError):
        failures.append("invalid_timestamp")
    if not isinstance(raw,bytes) or not raw:
        failures.append("empty_raw")
    elif manifest.get("raw_sha256")!=hashlib.sha256(raw).hexdigest():
        failures.append("checksum_mismatch")
    for field in ("delistings_included","missing_sessions_audited"):
        if manifest.get(field) is not True:
            failures.append("not_verified_"+field)
    try:
        start=datetime.fromisoformat(manifest["historical_span_start"]).date()
        end=datetime.fromisoformat(manifest["historical_span_end"]).date()
        if start>=end:
            failures.append("invalid_span")
    except (KeyError,ValueError,TypeError):
        failures.append("invalid_span")
    return {"admitted":not failures,"failures":sorted(set(failures)),
            "interpretation":"provenance_gate_only_not_predictive_validation"}


def inspect_manifest_file(manifest_path:Path, raw_path:Path, *, evaluation_utc:str)->dict:
    return validate_manifest(json.loads(manifest_path.read_text(encoding="utf-8")),
                             raw_path.read_bytes(),evaluation_utc=evaluation_utc)
