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
    def __init__(self, status=200, payload=None, content_type="application/json", json_error=None, headers=None):
        self.status_code = status
        self._payload = payload
        self._json_error = json_error
        self.headers = {"content-type": content_type}
        self.headers.update(headers or {})
        self.closed = False

    def json(self):
        if self._json_error:
            raise self._json_error
        return self._payload

    def close(self):
        self.closed = True


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.headers = {}

    def get(self, url, timeout=20, **kwargs):
        self.calls.append({"url": url, "timeout": timeout, **kwargs})
        if not self.responses:
            raise RuntimeError("no response fixture")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class SecEndpointProbeTests(unittest.TestCase):
    def _snapshot(self, directory, mapping=None):
        path = Path(directory) / "sec_ticker_map.json"
        sec_enrich._write_ticker_snapshot(
            mapping or {"AAPL": 320193, "MSFT": 789019, "NVDA": 1045810},
            sec_enrich.TICKERS_EXCHANGE,
            path,
        )
        return path

    def _bulk_ok(self, status=206):
        return FakeResponse(
            status=status,
            payload=None,
            content_type="application/zip",
            headers={"content-range": "bytes 0-0/123456", "content-length": "1", "accept-ranges": "bytes"},
        )

    def _archive_ok(self, status=206, content_type="text/plain"):
        return FakeResponse(
            status=status,
            payload=None,
            content_type=content_type,
            headers={"content-range": "bytes 0-0/654321", "content-length": "1", "accept-ranges": "bytes"},
        )

    def test_probe_reports_companyfacts_submissions_and_bulk_availability(self):
        facts = {"facts": {"us-gaap": {"Assets": {}}}}
        submissions = {"filings": {"recent": {"form": ["10-K"]}}}
        session = FakeSession([
            FakeResponse(payload=facts), FakeResponse(payload=submissions),
            FakeResponse(payload=facts), FakeResponse(payload=submissions),
            FakeResponse(payload=facts), FakeResponse(payload=submissions),
            self._bulk_ok(), self._bulk_ok(),
        ])
        with tempfile.TemporaryDirectory() as tmp:
            report = probe.probe(session=session, snapshot_path=self._snapshot(tmp), archive_endpoints={})
        self.assertTrue(report["snapshot_available"])
        self.assertEqual(report["snapshot_count"], 3)
        self.assertEqual(report["summary"], {
            "requests": 6, "http_ok": 6, "payload_ok": 6,
            "bulk_requests": 2, "bulk_ok": 2,
            "archive_requests": 0, "archive_ok": 0,
        })
        self.assertTrue(report["sentinels"]["AAPL"]["companyfacts"]["payload_present"])
        self.assertTrue(report["sentinels"]["AAPL"]["submissions"]["payload_present"])
        self.assertEqual(report["bulk"]["companyfacts_zip"]["status"], 206)
        self.assertEqual(report["bulk"]["submissions_zip"]["content_range"], "bytes 0-0/123456")
        self.assertEqual(len(session.calls), 8)
        for call in session.calls[-2:]:
            self.assertTrue(call["stream"])
            self.assertEqual(call["headers"]["Range"], "bytes=0-0")

    def test_http_failure_is_diagnostic_not_exception(self):
        session = FakeSession([
            FakeResponse(status=403, payload={}),
            FakeResponse(status=403, payload={}),
            FakeResponse(status=403, content_type="text/html"),
            FakeResponse(status=403, content_type="text/html"),
        ])
        with tempfile.TemporaryDirectory() as tmp:
            path = self._snapshot(tmp, {"AAPL": 320193})
            report = probe.probe(session=session, snapshot_path=path, sentinels=("AAPL",), archive_endpoints={})
        self.assertEqual(report["summary"], {
            "requests": 2, "http_ok": 0, "payload_ok": 0,
            "bulk_requests": 2, "bulk_ok": 0,
            "archive_requests": 0, "archive_ok": 0,
        })
        self.assertEqual(report["sentinels"]["AAPL"]["companyfacts"]["status"], 403)
        self.assertEqual(report["sentinels"]["AAPL"]["submissions"]["status"], 403)
        self.assertEqual(report["bulk"]["companyfacts_zip"]["status"], 403)

    def test_invalid_json_is_separated_from_http_failure(self):
        session = FakeSession([
            FakeResponse(status=200, json_error=ValueError("html"), content_type="text/html"),
            FakeResponse(status=200, payload={"filings": {"recent": {}}}),
            self._bulk_ok(), self._bulk_ok(),
        ])
        with tempfile.TemporaryDirectory() as tmp:
            path = self._snapshot(tmp, {"AAPL": 320193})
            report = probe.probe(session=session, snapshot_path=path, sentinels=("AAPL",), archive_endpoints={})
        cf = report["sentinels"]["AAPL"]["companyfacts"]
        self.assertTrue(cf["ok"])
        self.assertFalse(cf["json_valid"])
        self.assertEqual(cf["content_type"], "text/html")
        self.assertEqual(report["summary"]["http_ok"], 2)
        self.assertEqual(report["summary"]["payload_ok"], 1)
        self.assertEqual(report["summary"]["bulk_ok"], 2)

    def test_missing_snapshot_still_probes_official_bulk_archives(self):
        session = FakeSession([self._bulk_ok(), self._bulk_ok(status=200)])
        with tempfile.TemporaryDirectory() as tmp:
            report = probe.probe(
                session=session,
                snapshot_path=Path(tmp) / "missing.json",
                archive_endpoints={},
            )
        self.assertFalse(report["snapshot_available"])
        self.assertEqual(report["summary"], {
            "requests": 0, "http_ok": 0, "payload_ok": 0,
            "bulk_requests": 2, "bulk_ok": 2,
            "archive_requests": 0, "archive_ok": 0,
        })
        self.assertEqual(len(session.calls), 2)

    def test_archive_paths_are_probed_independently_of_api_guard(self):
        archives = {
            "master": "https://www.sec.gov/Archives/edgar/full-index/2026/QTR3/master.idx",
            "xbrl": "https://www.sec.gov/Archives/edgar/data/320193/example.xml",
        }
        session = FakeSession([
            self._bulk_ok(status=403), self._bulk_ok(status=403),
            self._archive_ok(), self._archive_ok(content_type="application/xml"),
        ])
        with tempfile.TemporaryDirectory() as tmp:
            report = probe.probe(
                session=session,
                snapshot_path=Path(tmp) / "missing.json",
                archive_endpoints=archives,
            )
        self.assertEqual(report["summary"]["bulk_ok"], 0)
        self.assertEqual(report["summary"]["archive_requests"], 2)
        self.assertEqual(report["summary"]["archive_ok"], 2)
        self.assertTrue(report["archives"]["master"]["ok"])
        self.assertEqual(report["archives"]["xbrl"]["content_type"], "application/xml")
        for call in session.calls[-2:]:
            self.assertTrue(call["stream"])
            self.assertEqual(call["headers"]["Range"], "bytes=0-0")


if __name__ == "__main__":
    unittest.main(verbosity=2)
