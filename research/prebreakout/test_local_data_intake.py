#!/usr/bin/env python3
"""Contract tests use synthetic fixtures; no real historical evidence."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from local_data_intake import intake

CSV = b"symbol,session,open,high,low,close,volume\nTEST,2025-01-02,10,12,9,11,100\n"
CAL = "2025-01-02\n2025-01-03\n2025-01-06\n"


def manifest(raw):
    return {
        "dataset_id":"synthetic", "vendor":"unit_test", "license":"testing_only",
        "source_uri":"synthetic://fixture", "raw_sha256":hashlib.sha256(raw).hexdigest(),
        "collected_at_utc":"2025-01-07T00:00:00Z",
        "available_at_utc":"2025-01-07T00:00:00Z",
        "universe_asof_method":"fixture", "delistings_included":True,
        "corporate_actions_method":"fixture", "price_adjustment":"fixture",
        "trading_calendar":"synthetic", "currency_units":"USD",
        "sector_asof_method":"fixture", "benchmark_asof_method":"fixture",
        "missing_sessions_audited":True,
        "historical_span_start":"2025-01-01","historical_span_end":"2025-01-08"
    }


class LocalIntakeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root=Path(self.tmp.name)
        self.raw=root/"prices.csv"
        self.meta=root/"manifest.json"
        self.calendar=root/"calendar.txt"
        self.write_fixture()

    def write_fixture(self, raw=CSV, calendar=CAL, meta=None):
        self.raw.write_bytes(raw)
        self.meta.write_text(json.dumps(manifest(CSV) if meta is None else meta))
        self.calendar.write_text(calendar)

    def run_intake(self):
        return intake(self.raw,self.meta,self.calendar,evaluation_utc="2025-01-08T00:00:00Z")

    def test_valid_synthetic_structure_never_certified(self):
        result=self.run_intake()
        self.assertEqual(result["status"],"STRUCTURAL_CHECKS_PASSED_NOT_PIT_CERTIFIED")
        self.assertFalse(result["empirical_validated"])

    def test_missing_raw_blocks(self):
        self.raw.unlink()
        self.assertEqual(self.run_intake()["status"],"BLOCKED_DATA_ACCESS")

    def test_missing_calendar_blocks(self):
        self.calendar.unlink()
        self.assertEqual(self.run_intake()["status"],"BLOCKED_DATA_ACCESS")

    def test_modified_raw_fails_checksum(self):
        self.write_fixture(raw=CSV.replace(b"100",b"200"))
        self.assertIn("checksum_mismatch",self.run_intake()["provenance"]["failures"])

    def test_off_calendar_observation_rejected(self):
        self.write_fixture(calendar="2025-01-03\n2025-01-06\n")
        self.assertIn("session_outside_calendar",self.run_intake()["observations"]["failures"])

    def test_invalid_prices_rejected(self):
        raw=CSV.replace(b",12,9,11",b",8,9,11")
        self.write_fixture(raw=raw,meta=manifest(raw))
        self.assertIn("inconsistent_ohlc",self.run_intake()["observations"]["failures"])

    def test_bad_manifest_rejected(self):
        self.meta.write_text("{unparseable")
        self.assertEqual(self.run_intake()["status"],"REJECTED_INPUT")

if __name__=="__main__":
    unittest.main()
