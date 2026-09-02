import hashlib
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

if "requests" not in sys.modules:
    requests_stub = types.ModuleType("requests")
    requests_stub.Session = object
    sys.modules["requests"] = requests_stub

import seed_sec_ticker_map as seed


class FakeResponse:
    def __init__(self, content=b"", status=200):
        self.content = content
        self.status_code = status
        self.ok = 200 <= status < 300


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.urls = []

    def get(self, url, timeout=30):
        self.urls.append((url, timeout))
        return self.response


def fixture_bytes(rows=None):
    rows = rows or [
        [320193, "Apple Inc.", "AAPL", "Nasdaq"],
        [789019, "MICROSOFT CORP", "MSFT", "Nasdaq"],
        [1045810, "NVIDIA CORP", "NVDA", "Nasdaq"],
    ]
    return json.dumps({"fields": seed.EXPECTED_FIELDS, "data": rows}, separators=(",", ":")).encode("utf-8")


class SeedSecTickerMapTests(unittest.TestCase):
    def test_constants_pin_immutable_transport_and_official_source(self):
        self.assertEqual(len(seed.MIRROR_COMMIT), 40)
        self.assertIn(seed.MIRROR_COMMIT, seed.MIRROR_URL)
        self.assertEqual(len(seed.EXPECTED_SHA256), 64)
        self.assertEqual(seed.TICKERS_EXCHANGE, "https://www.sec.gov/files/company_tickers_exchange.json")
        self.assertEqual(seed.EXPECTED_RECORDS, 10432)

    def test_verified_mapping_rejects_checksum_mismatch(self):
        raw = fixture_bytes()
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            seed._verified_mapping(raw)

    def test_verified_mapping_checks_schema_count_and_sentinels_after_hash(self):
        raw = fixture_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        with mock.patch.object(seed, "EXPECTED_SHA256", digest), mock.patch.object(seed, "EXPECTED_RECORDS", 3):
            mapping, actual = seed._verified_mapping(raw)
        self.assertEqual(actual, digest)
        self.assertEqual(mapping["AAPL"], 320193)
        self.assertEqual(mapping["MSFT"], 789019)
        self.assertEqual(mapping["NVDA"], 1045810)

    def test_wrong_sentinel_is_rejected_even_with_matching_hash(self):
        raw = fixture_bytes([
            [999, "Apple Inc.", "AAPL", "Nasdaq"],
            [789019, "MICROSOFT CORP", "MSFT", "Nasdaq"],
            [1045810, "NVIDIA CORP", "NVDA", "Nasdaq"],
        ])
        digest = hashlib.sha256(raw).hexdigest()
        with mock.patch.object(seed, "EXPECTED_SHA256", digest), mock.patch.object(seed, "EXPECTED_RECORDS", 3):
            with self.assertRaisesRegex(ValueError, "sentinel mismatch"):
                seed._verified_mapping(raw)

    def test_existing_valid_snapshot_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sec_ticker_map.json"
            payload = {
                "schema_version": 1,
                "generated_at": "2026-09-02T00:00:00+00:00",
                "source": seed.TICKERS_EXCHANGE,
                "count": 1,
                "map": {"AAPL": 320193},
            }
            path.write_text(json.dumps(payload), encoding="utf-8")
            session = FakeSession(FakeResponse(status=500))
            mapping, kept, created = seed.seed_snapshot(session=session, path=path)
            self.assertFalse(created)
            self.assertEqual(mapping, {"AAPL": 320193})
            self.assertEqual(kept["source"], seed.TICKERS_EXCHANGE)
            self.assertEqual(session.urls, [])

    def test_verified_transport_writes_sec_source_and_transport_metadata(self):
        raw = fixture_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sec_ticker_map.json"
            session = FakeSession(FakeResponse(raw))
            with mock.patch.object(seed, "EXPECTED_SHA256", digest), mock.patch.object(seed, "EXPECTED_RECORDS", 3), mock.patch.object(seed, "_validated_map", side_effect=lambda m: m if m else None):
                # The production guard requires >10k mappings. This unit fixture
                # patches only that volume guard while retaining schema/sentinel checks.
                with mock.patch.object(seed, "_verified_mapping", return_value=({"AAPL": 320193, "MSFT": 789019, "NVDA": 1045810}, digest)):
                    mapping, payload, created = seed.seed_snapshot(session=session, path=path)
            self.assertTrue(created)
            self.assertEqual(mapping["AAPL"], 320193)
            self.assertEqual(payload["source"], seed.TICKERS_EXCHANGE)
            self.assertEqual(payload["transport"], "pinned_github_mirror")
            self.assertEqual(payload["transport_commit"], seed.MIRROR_COMMIT)
            self.assertEqual(payload["upstream_sha256"], digest)
            on_disk = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(on_disk["source"], seed.TICKERS_EXCHANGE)


if __name__ == "__main__":
    unittest.main(verbosity=2)
