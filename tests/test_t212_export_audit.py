"""Synthetic tests for the local Trading 212 export identity audit."""
import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("t212_audit", ROOT / "scripts/audit_t212_exports.py")
audit_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit_module)

FIELDS = ["Action", "Time", "ID", "No. of shares", "Price / share",
          "Total", "Ticker", "ISIN", "Name", "Notes"]


class Trading212ExportAuditTests(unittest.TestCase):
    def write(self, folder, name, rows):
        path = Path(folder) / name
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        return path

    def test_idless_dividends_and_distinct_official_ids(self):
        with tempfile.TemporaryDirectory() as folder:
            base = dict(Action="Dividend (Dividend)", Time="2026-01-02 10:00:00",
                        ID="", Ticker="TEST", ISIN="US0000000000", Name="Test",
                        Notes="", **{"No. of shares": "1", "Price / share": "0.2", "Total": "0.20"})
            rows = [base, {**base, "Time": "2026-01-03 10:00:00"},
                    {**base, "Action": "Market buy", "ID": "official-1"},
                    {**base, "Action": "Market buy", "ID": "official-2"}]
            result = audit_module.audit([self.write(folder, "export.csv", rows)])
            self.assertTrue(result["identity_check_passed"])
            self.assertEqual(result["missing_id_rows"], 2)
            self.assertEqual(result["ambiguous_no_id_fingerprint_groups"], 0)

    def test_idless_exact_collision_is_flagged(self):
        with tempfile.TemporaryDirectory() as folder:
            row = dict(Action="Dividend (Dividend)", Time="2026-01-02 10:00:00",
                       ID="", Ticker="TEST", ISIN="", Name="Test", Notes="",
                       **{"No. of shares": "1", "Price / share": "0.2", "Total": "0.20"})
            result = audit_module.audit([self.write(folder, "export.csv", [row, row])])
            self.assertFalse(result["identity_check_passed"])
            self.assertEqual(result["ambiguous_no_id_fingerprint_groups"], 1)


if __name__ == "__main__":
    unittest.main()
