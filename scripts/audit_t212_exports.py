#!/usr/bin/env python3
"""Local-only Trading 212 CSV integrity audit. Never uploads account data.

Usage: python scripts/audit_t212_exports.py export-2023.csv export-2024.csv
Exit 1 on conflicting official IDs or fingerprint collisions among ID-less rows.
A clean result proves identity consistency only, NOT holdings/P&L reconciliation.
"""
import argparse
import collections
import csv
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path


def amount(value, places):
    try:
        return str(Decimal(str(value or "0")).quantize(Decimal(places)))
    except InvalidOperation:
        raise ValueError("Invalid numeric field in export") from None


def identity(row):
    official_id = str(row.get("ID") or "").strip()
    action = str(row.get("Action") or "").strip()
    if official_id:
        return ("official", action, official_id)
    qty = Decimal(str(row.get("No. of shares") or "0"))
    price = Decimal(str(row.get("Price / share") or "0"))
    return (
        "fallback", action,
        str(row.get("Time") or row.get("Time (UTC)") or "").strip(),
        str(row.get("Ticker") or "").strip(),
        str(row.get("ISIN") or "").strip(),
        str(row.get("Name") or "").strip(),
        amount(qty, "0.00000001"),
        amount(row.get("Total"), "0.01"),
        amount(qty * price, "0.00000001"),
        str(row.get("Notes") or "").strip(),
    )


def audit(paths):
    rows = []
    for path in paths:
        with open(path, encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            required = {"ID", "Action", "No. of shares", "Total"}
            if not required.issubset(reader.fieldnames or []):
                raise ValueError(f"{Path(path).name}: missing Trading 212 columns")
            if not ({"Time", "Time (UTC)"} & set(reader.fieldnames or [])):
                raise ValueError(f"{Path(path).name}: missing Time column")
            rows.extend(reader)
    counts = collections.Counter(identity(row) for row in rows)
    no_id = [row for row in rows if not str(row.get("ID") or "").strip()]
    # Repeated exports can overlap legitimately. Report repeated identities, not
    # merely repeated files, and distinguish no-ID ambiguity from official IDs.
    collisions = [key for key, n in counts.items() if n > 1 and key[0] == "fallback"]
    repeated_official = sum(n - 1 for key, n in counts.items() if n > 1 and key[0] == "official")
    return {
        "files": len(paths), "rows": len(rows),
        "official_id_rows": len(rows) - len(no_id),
        "missing_id_rows": len(no_id),
        "missing_id_by_action": dict(sorted(collections.Counter(row["Action"] for row in no_id).items())),
        "repeated_official_id_rows": repeated_official,
        "ambiguous_no_id_fingerprint_groups": len(collisions),
        "identity_check_passed": not collisions,
        "scope": "Identity consistency only; no balances, holdings, tax or P&L reconciliation",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", nargs="+", help="Local Trading 212 export CSV files")
    args = parser.parse_args()
    result = audit(args.csv)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["identity_check_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
