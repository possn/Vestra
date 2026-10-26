#!/usr/bin/env python3
import hashlib
import unittest
from pit_dataset_gate import validate_manifest


def fixture(raw=b"OHLCV"):
    return dict(dataset_id="test",vendor="synthetic",license="testing_only",
      source_uri="synthetic://unit-test",raw_sha256=hashlib.sha256(raw).hexdigest(),
      collected_at_utc="2026-01-05T00:00:00Z",available_at_utc="2026-01-04T00:00:00Z",
      universe_asof_method="archived_snapshot",delistings_included=True,
      corporate_actions_method="point_in_time",price_adjustment="split_adjusted",
      trading_calendar="named_exchange",currency_units="USD",sector_asof_method="historical",
      benchmark_asof_method="historical",missing_sessions_audited=True,
      historical_span_start="2015-01-01",historical_span_end="2025-12-31")


class DataGateTests(unittest.TestCase):
    def test_complete_manifest_admitted(self):
        result=validate_manifest(fixture(),b"OHLCV",evaluation_utc="2026-01-06T00:00:00Z")
        self.assertTrue(result["admitted"])
    def test_raw_content_tamper_rejected(self):
        result=validate_manifest(fixture(),b"ALTERED",evaluation_utc="2026-01-06T00:00:00Z")
        self.assertIn("checksum_mismatch",result["failures"])
    def test_future_data_cannot_be_used(self):
        m=fixture();m["available_at_utc"]="2026-02-01T00:00:00Z"
        self.assertIn("future_availability",validate_manifest(m,b"OHLCV",evaluation_utc="2026-01-06T00:00:00Z")["failures"])
    def test_missing_delistings_rejected(self):
        m=fixture();m["delistings_included"]=False
        self.assertIn("not_verified_delistings_included",validate_manifest(m,b"OHLCV",evaluation_utc="2026-01-06T00:00:00Z")["failures"])
    def test_missing_fields_rejected(self):
        m=fixture();del m["trading_calendar"]
        self.assertIn("missing_trading_calendar",validate_manifest(m,b"OHLCV",evaluation_utc="2026-01-06T00:00:00Z")["failures"])


if __name__=="__main__":
    unittest.main()
