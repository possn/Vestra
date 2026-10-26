#!/usr/bin/env python3
"""Offline licensed CSV intake: checks raw bytes and observed rows; never certifies PIT or alpha."""
import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path

from pit_dataset_gate import validate_manifest
from ohlcv_observation_audit import audit_ohlcv_rows


def intake(raw_path, manifest_path, calendar_path, *, evaluation_utc):
    missing = [name for name, path in (("raw",raw_path),("manifest",manifest_path),
                                     ("calendar",calendar_path)) if not Path(path).is_file()]
    if missing:
        return {"status":"BLOCKED_DATA_ACCESS","missing":missing,"empirical_validated":False}
    try:
        raw = Path(raw_path).read_bytes()
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
        calendar = [v.strip() for v in Path(calendar_path).read_text(encoding="utf-8").splitlines() if v.strip()]
        provenance = validate_manifest(manifest,raw,evaluation_utc=evaluation_utc)
        rows = list(csv.DictReader(raw.decode("utf-8-sig").splitlines()))
        cutoff = datetime.fromisoformat(evaluation_utc.replace("Z","+00:00")).date().isoformat()
        observations = audit_ohlcv_rows(rows,reference_sessions=calendar,evaluation_date=cutoff)
    except (OSError, UnicodeError, ValueError, TypeError, csv.Error, json.JSONDecodeError) as exc:
        return {"status":"REJECTED_INPUT","reason":type(exc).__name__,"empirical_validated":False}
    return {"status":"STRUCTURAL_CHECKS_PASSED_NOT_PIT_CERTIFIED"
            if provenance["admitted"] and observations["admitted"] else "REJECTED_INPUT",
            "provenance":provenance,"observations":observations,
            "empirical_validated":False,
            "limitations":["manifest_claims_and_checksum_do_not_authenticate_vendor",
                           "exchange_calendar_must_be_independently_verified",
                           "no_universe_delisting_corporate_action_or_pit_certification",
                           "no_returns_or_alpha_claims"]}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw",required=True,help="Private licensed OHLCV CSV")
    parser.add_argument("--manifest",required=True,help="Provenance JSON for exact CSV bytes")
    parser.add_argument("--calendar",required=True,help="Independent exchange session dates, one per line")
    parser.add_argument("--evaluation-utc",default=datetime.now(timezone.utc).isoformat())
    args=parser.parse_args()
    result=intake(args.raw,args.manifest,args.calendar,evaluation_utc=args.evaluation_utc)
    print(json.dumps(result,sort_keys=True,allow_nan=False))
    return 0 if result["status"]=="STRUCTURAL_CHECKS_PASSED_NOT_PIT_CERTIFIED" else 2

if __name__=="__main__":
    raise SystemExit(main())
