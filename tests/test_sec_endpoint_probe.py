import json
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

if "requests" not in sys.modules:
    requests_stub = types.ModuleType("requests")
    requests_stub.Session = object
    sys.modules["requests"] = requests_stub

import sec_enrich
import sec_endpoint_probe as probe


class FakeResponse:
    def __init__(self, status=200, payload=None, content_type="application/json", json_error=None):
        self.status_code = status
        self._payload = payload
        self._json_error = json_error
        self.headers = {"content-type": content_type}

    def json(self):
        if self._json_error:
            raise self._json_error
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.urls = []
        self.headers = {}

    def get(self, url, timeout=20):
        self.urls.append((url, timeout))
        if not self.responses:
            raise RuntimeError("no response fixture")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class SecEndpointProbeTests(unittest.TestCase):
    def _snapshot(self, directory):
        path = Path(directory) / "sec_ticker_map.json"
        sec_enrich._write_ticker_snapshot(
            {"AAPL": 320193, "MSFT": 789019, "NVDA": 1045810},
            sec_enrich.TICKERS_EXCHANGE,
            path,
        )
        return path

    def test_probe_reports_companyfacts_and_submissions_payloads(self):
        facts = {"facts": {"us-gaap": {"Assets": {}}}}
        submissions = {"filings": {"recent": {"form": ["10-K"]}}}
        session = FakeSession([
            FakeResponse(payload=facts), FakeResponse(payload=submissions),
            FakeResponse(payload=facts), FakeResponse(payload=submissions),
            FakeResponse(payload=facts), FakeResponse(payload=submissions),
        ])
        with tempfile.TemporaryDirectory() as tmp:
            report = probe.probe(session=session, snapshot_path=self._snapshot(tmp))
        self.assertTrue(report["snapshot_available"])
        self.assertEqual(report["snapshot_count"], 3)
        self.assertEqual(report["summary"], {"requests": 6, "http_ok": 6, "payload_ok": 6})
        self.assertTrue(report["sentinels"]["AAPL"]["companyfacts"]["payload_present"])
        self.assertTrue(report["sentinels"]["AAPL"]["submissions"]["payload_present"])
        self.assertEqual(len(session.urls), 6)

    def test_http_failure_is_diagnostic_not_exception(self):
        session = FakeSession([
            FakeResponse(status=403, payload={}),
            FakeResponse(status=403, payload={}),
        ])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sec_ticker_map.json"
            sec_enrich._write_ticker_snapshot({"AAPL": 320193}, sec_enrich.TICKERS_EXCHANGE, path)
            report = probe.probe(session=session, snapshot_path=path, sentinels=("AAPL",))
        self.assertEqual(report["summary"], {"requests": 2, "http_ok": 0, "payload_ok": 0})
        self.assertEqual(report["sentinels"]["AAPL"]["companyfacts"]["status"], 403)
        self.assertEqual(report["sentinels"]["AAPL"]["submissions"]["status"], 403)

    def test_invalid_json_is_separated_from_http_failure(self):
        session = FakeSession([
            FakeResponse(status=200, json_error=ValueError("html"), content_type="text/html"),
            FakeResponse(status=200, payload={"filings": {"recent": {}}}),
        ])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sec_ticker_map.json"
            sec_enrich._write_ticker_snapshot({"AAPL": 320193}, sec_enrich.TICKERS_EXCHANGE, path)
            report = probe.probe(session=session, snapshot_path=path, sentinels=("AAPL",))
        cf = report["sentinels"]["AAPL"]["companyfacts"]
        self.assertTrue(cf["ok"])
        self.assertFalse(cf["json_valid"])
        self.assertEqual(cf["content_type"], "text/html")
        self.assertEqual(report["summary"]["http_ok"], 2)
        self.assertEqual(report["summary"]["payload_ok"], 1)

    def test_missing_snapshot_makes_zero_requests(self):
        session = FakeSession([])
        with tempfile.TemporaryDirectory() as tmp:
            report = probe.probe(session=session, snapshot_path=Path(tmp) / "missing.json")
        self.assertFalse(report["snapshot_available"])
        self.assertEqual(report["summary"], {"requests": 0, "http_ok": 0, "payload_ok": 0})
        self.assertEqual(session.urls, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
