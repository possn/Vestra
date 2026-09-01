import json
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

# Architecture invariants intentionally do not install the heavy market pipeline
# requirements. These tests exercise only the pure ticker-map helpers and inject
# their own fake sessions, so a minimal import stub keeps the contract unit-level.
if "requests" not in sys.modules:
    requests_stub = types.ModuleType("requests")
    requests_stub.Session = object
    sys.modules["requests"] = requests_stub

import sec_enrich


class FakeResponse:
    def __init__(self, payload=None, status=200, json_error=None):
        self._payload = payload
        self.status_code = status
        self.ok = 200 <= status < 300
        self._json_error = json_error

    def json(self):
        if self._json_error:
            raise self._json_error
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.urls = []

    def get(self, url, timeout=20):
        self.urls.append(url)
        if not self.responses:
            raise RuntimeError("no response fixture")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class SecTickerMapResilienceTests(unittest.TestCase):
    def test_parses_primary_official_schema_exactly(self):
        payload = {
            "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
            "1": {"cik_str": 789019, "ticker": "MSFT", "title": "Microsoft Corp"},
        }
        self.assertEqual(sec_enrich._parse_company_tickers(payload), {"AAPL": 320193, "MSFT": 789019})

    def test_parses_exchange_official_schema_by_field_names(self):
        payload = {
            "fields": ["name", "exchange", "ticker", "cik"],
            "data": [
                ["Apple Inc.", "Nasdaq", "AAPL", 320193],
                ["Microsoft Corp", "Nasdaq", "MSFT", 789019],
            ],
        }
        self.assertEqual(sec_enrich._parse_company_tickers_exchange(payload), {"AAPL": 320193, "MSFT": 789019})

    def test_malformed_primary_falls_through_to_exchange_source(self):
        exchange = {
            "fields": ["cik", "name", "ticker", "exchange"],
            "data": [[320193, "Apple Inc.", "AAPL", "Nasdaq"]],
        }
        session = FakeSession([
            FakeResponse(json_error=ValueError("HTML response")),
            FakeResponse(json_error=ValueError("HTML response again")),
            FakeResponse(exchange),
        ])
        mapping, source = sec_enrich._remote_ticker_map(session, retries=2, sleep=lambda _: None)
        self.assertEqual(mapping, {"AAPL": 320193})
        self.assertEqual(source, sec_enrich.TICKERS_EXCHANGE)
        self.assertEqual(session.urls[:2], [sec_enrich.TICKERS, sec_enrich.TICKERS])
        self.assertEqual(session.urls[2], sec_enrich.TICKERS_EXCHANGE)

    def test_remote_failure_uses_last_valid_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sec_ticker_map.json"
            sec_enrich._write_ticker_snapshot({"AAPL": 320193}, "fixture", path)
            session = FakeSession([
                RuntimeError("network down"),
                RuntimeError("network down"),
            ])
            mapping = sec_enrich._load_ticker_map(session, snapshot_path=path, retries=1, sleep=lambda _: None)
            self.assertEqual(mapping, {"AAPL": 320193})

    def test_remote_success_persists_snapshot_for_later_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sec_ticker_map.json"
            primary = {"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}}
            mapping = sec_enrich._load_ticker_map(
                FakeSession([FakeResponse(primary)]),
                snapshot_path=path,
                retries=1,
                sleep=lambda _: None,
            )
            self.assertEqual(mapping, {"AAPL": 320193})
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema_version"], 1)
            self.assertEqual(payload["count"], 1)
            self.assertEqual(payload["map"], {"AAPL": 320193})
            self.assertEqual(payload["source"], sec_enrich.TICKERS)

    def test_malformed_snapshot_is_rejected_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sec_ticker_map.json"
            path.write_text(json.dumps({
                "schema_version": 1,
                "count": 2,
                "map": {"AAPL": 320193, "NOT A TICKER": 123},
            }), encoding="utf-8")
            self.assertIsNone(sec_enrich._read_ticker_snapshot(path))

    def test_no_fuzzy_or_company_name_matching(self):
        payload = {
            "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
        }
        mapping = sec_enrich._parse_company_tickers(payload)
        self.assertNotIn("APPLE", mapping)
        self.assertNotIn("AAPL.US", mapping)
        self.assertEqual(mapping.get("AAPL"), 320193)


if __name__ == "__main__":
    unittest.main()
