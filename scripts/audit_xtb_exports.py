#!/usr/bin/env python3
"""Offline XTB workbook controls; no broker data is sent to GitHub.

Reads .xlsx XML using only Python's standard library. Prints aggregated controls,
not account numbers or transaction-level personal data.
"""
import argparse
import collections
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from decimal import Decimal, InvalidOperation

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def sheet_rows(archive, sheet_number, strings):
    root = ET.fromstring(archive.read(f"xl/worksheets/sheet{sheet_number}.xml"))
    for row in root.findall(f".//{NS}sheetData/{NS}row"):
        values = {}
        for cell in row.findall(f"{NS}c"):
            column = re.match(r"[A-Z]+", cell.attrib["r"]).group()
            value = cell.find(f"{NS}v")
            raw = value.text if value is not None and value.text else ""
            if cell.attrib.get("t") == "s" and raw:
                raw = strings[int(raw)]
            elif cell.attrib.get("t") == "inlineStr":
                raw = "".join(cell.itertext())
            values[column] = raw
        yield values


def as_decimal(value):
    try:
        return Decimal(str(value or "0"))
    except InvalidOperation:
        raise ValueError("Non-numeric amount in XTB workbook") from None


def audit(path):
    with zipfile.ZipFile(path) as archive:
        strings = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            strings = ["".join(t.text or "" for t in item.iter(f"{NS}t")) for item in root]
        cash = list(sheet_rows(archive, 2, strings))
        positions = list(sheet_rows(archive, 3, strings))
    if not any(row.get("A") == "Type" and row.get("F") == "Amount" and row.get("G") == "ID" for row in cash[:10]):
        raise ValueError("Unexpected XTB Cash Operations layout")
    header = next(i for i, row in enumerate(cash) if row.get("A") == "Type" and row.get("G") == "ID")
    transactions = [row for row in cash[header + 1:] if row.get("G")]
    ids = [row["G"] for row in transactions]
    by_type = collections.Counter(row.get("A", "") for row in transactions)
    sums = collections.defaultdict(Decimal)
    for row in transactions:
        sums[row.get("A", "")] += as_decimal(row.get("F"))
    metric_rows = [row for row in positions if row.get("B") in ("Value", "Profit") and row.get("A") in ("My Trades", "Investment Plans")]
    metrics = {f"{row['A']} {row['B']}": str(as_decimal(row.get("C"))) for row in metric_rows}
    values = [as_decimal(row["C"]) for row in metric_rows if row["B"] == "Value"]
    return {
        "cash_operations": len(transactions),
        "unique_cash_operation_ids": len(set(ids)),
        "duplicate_cash_operation_ids": len(ids) - len(set(ids)),
        "cash_operations_by_type": dict(sorted(by_type.items())),
        "cash_totals_by_type_eur": {key: str(value) for key, value in sorted(sums.items())},
        "open_position_summary_eur": metrics,
        "total_reported_open_position_value_eur": str(sum(values, Decimal("0"))),
        "identity_check_passed": len(ids) == len(set(ids)),
        "scope": "XTB export controls only; no independent Vestra holdings or P&L reconciliation",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("xlsx", help="Local XTB export workbook")
    args = parser.parse_args()
    result = audit(args.xlsx)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["identity_check_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
