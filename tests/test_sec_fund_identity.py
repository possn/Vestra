import json
import tempfile
import unittest
from pathlib import Path

from scripts import sec_fund_identity as sfi


class _Response:
    def __init__(self, payload=None, error=None):
        self.payload = payload
        self.error = error

    def raise_for_status(self):
        if self.error:
            raise self.error

    def json(self):
        return self.payload


class _Session:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0
        self.urls = []

    def get(self, url, timeout=None):
        self.calls += 1
        self.urls.append(url)
        return self.responses.pop(0)


def _valid_payload(count=1000):
    rows = [[1000 + i, f"S{i}", f"C{i}", f"F{i}"] for i in range(count)]
    return {"fields": ["cik", "seriesId", "classId", "symbol"], "data": rows}


class SecFundIdentityTests(unittest.TestCase):
    def test_parses_official_fields_data_schema(self):
        payload = {
            "fields": ["cik", "seriesId", "classId", "symbol"],
            "data": [
                [1234, "S000001", "C000001", "BUG"],
                [5678, "S000002", "C000002", "CHAT"],
            ],
        }
        parsed = sfi.parse_sec_fund_payload(payload)
        self.assertEqual(parsed["BUG"]["cik"], 1234)
        self.assertEqual(parsed["BUG"]["series_id"], "S000001")
        self.assertEqual(parsed["CHAT"]["class_id"], "C000002")

    def test_malformed_payload_fails_closed(self):
        self.assertEqual(sfi.parse_sec_fund_payload({"fields": ["ticker"], "data": [["BUG"]]}), {})
        self.assertEqual(sfi.parse_sec_fund_payload([]), {})

    def test_snapshot_roundtrip_is_validated_and_records_transport(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "fund-map.json"
            mapping = {"BUG": {"cik": 1234, "series_id": "S1", "class_id": "C1"}}
            sfi.write_snapshot(mapping, transport="vestra_worker", path=path)
            loaded, payload = sfi.read_snapshot(path)
            self.assertEqual(loaded, mapping)
            self.assertEqual(payload["count"], 1)
            self.assertEqual(payload["transport"], "vestra_worker")
            self.assertEqual(payload["source"], sfi.SEC_FUND_TICKERS)

    def test_fetch_remote_retries_http_failure_and_accepts_valid_map(self):
        session = _Session([_Response(error=RuntimeError("HTTP 403")), _Response(payload=_valid_payload())])
        mapping = sfi.fetch_remote(session=session, retries=2, sleep=lambda _: None)
        self.assertEqual(session.calls, 2)
        self.assertEqual(len(mapping), 1000)
        self.assertEqual(mapping["F0"]["cik"], 1000)

    def test_fetch_worker_uses_canonical_route_and_same_strict_parser(self):
        session = _Session([_Response(payload=_valid_payload())])
        mapping = sfi.fetch_via_worker(session=session, worker_url="https://worker.example")
        self.assertEqual(len(mapping), 1000)
        self.assertEqual(session.urls, ["https://worker.example/sec-fund-map"])

    def test_refresh_falls_back_from_sec_to_worker_before_snapshot(self):
        session = _Session([
            _Response(error=RuntimeError("HTTP 403")),
            _Response(error=RuntimeError("HTTP 403")),
            _Response(error=RuntimeError("HTTP 403")),
            _Response(payload=_valid_payload()),
        ])
        with tempfile.TemporaryDirectory() as td:
            old_snapshot = sfi.SNAPSHOT_PATH
            try:
                sfi.SNAPSHOT_PATH = Path(td) / "snapshot.json"
                mapping, state = sfi.refresh_snapshot(session=session)
            finally:
                sfi.SNAPSHOT_PATH = old_snapshot
        self.assertEqual(len(mapping), 1000)
        self.assertEqual(state, "remote_via_worker")
        self.assertTrue(session.urls[-1].endswith("/sec-fund-map"))

    def test_fetch_remote_rejects_small_or_malformed_payload(self):
        session = _Session([_Response(payload={"fields": ["cik", "symbol"], "data": [[1, "BUG"]]})])
        with self.assertRaises(RuntimeError):
            sfi.fetch_remote(session=session, retries=1, sleep=lambda _: None)

    def test_audit_separates_unresolved_and_explicit_conflicts(self):
        with tempfile.TemporaryDirectory() as td:
            stocks = Path(td) / "stocks.json"
            stocks.write_text(json.dumps({"stocks": [
                {"ticker": "BUG", "quote_type": None, "region": "United States"},
                {"ticker": "CHAT", "quote_type": "ETF", "region": "United States"},
                {"ticker": "ODD", "quote_type": "EQUITY", "region": "United States"},
                {"ticker": "AAPL", "quote_type": "EQUITY", "region": "United States"},
            ]}), encoding="utf-8")
            old_audit = sfi.AUDIT_PATH
            try:
                sfi.AUDIT_PATH = Path(td) / "audit.json"
                audit = sfi.build_audit(
                    {
                        "BUG": {"cik": 1},
                        "CHAT": {"cik": 2},
                        "ODD": {"cik": 3},
                    },
                    "test",
                    stocks_path=stocks,
                )
            finally:
                sfi.AUDIT_PATH = old_audit
            self.assertEqual(audit["unresolved_rows_confirmed_as_registered_funds"], 1)
            self.assertEqual(audit["explicit_non_equity_rows_confirmed"], 1)
            self.assertEqual(audit["explicit_equity_type_conflicts"], 1)
            self.assertEqual(audit["unresolved_examples"][0]["ticker"], "BUG")


if __name__ == "__main__":
    unittest.main()
