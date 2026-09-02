import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import sec_fund_identity as sfi


class _Response:
    def __init__(self, payload=None, text="", error=None):
        self.payload = payload
        self.text = text
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

    def get(self, url, timeout=None, headers=None):
        self.calls += 1
        self.urls.append(url)
        return self.responses.pop(0)


def _valid_payload(count=1000):
    rows = [[1000 + i, f"S{i}", f"C{i}", f"F{i}"] for i in range(count)]
    return {"fields": ["cik", "seriesId", "classId", "symbol"], "data": rows}


def _series_html(ticker="BUG"):
    return f"""
    <html><body><table>
      <tr><td><a>0001432353</a></td><td>Global X Funds</td></tr>
      <tr><td><a>S000066713</a></td><td>Global X Cybersecurity ETF</td></tr>
      <tr><td><a>C000214985</a></td><td>Global X Cybersecurity ETF</td><td>{ticker}</td></tr>
    </table></body></html>
    """


class SecFundIdentityTests(unittest.TestCase):
    def test_parses_official_fields_data_schema(self):
        payload = {
            "fields": ["cik", "seriesId", "classId", "symbol"],
            "data": [[1234, "S000001", "C000001", "BUG"]],
        }
        parsed = sfi.parse_sec_fund_payload(payload)
        self.assertEqual(parsed["BUG"]["cik"], 1234)
        self.assertEqual(parsed["BUG"]["series_id"], "S000001")

    def test_malformed_bulk_payload_fails_closed(self):
        self.assertEqual(sfi.parse_sec_fund_payload({"fields": ["ticker"], "data": [["BUG"]]}), {})

    def test_series_parser_carries_cik_and_series_context(self):
        item = sfi.parse_series_search_html(_series_html(), "BUG")
        self.assertEqual(item["cik"], 1432353)
        self.assertEqual(item["series_id"], "S000066713")
        self.assertEqual(item["class_id"], "C000214985")
        self.assertEqual(item["class_name"], "Global X Cybersecurity ETF")

    def test_series_parser_requires_exact_ticker_and_class_row(self):
        self.assertIsNone(sfi.parse_series_search_html(_series_html("BUGX"), "BUG"))
        echo_only = '<html><body><input value="BUG"><table><tr><td>BUG</td></tr></table></body></html>'
        self.assertIsNone(sfi.parse_series_search_html(echo_only, "BUG"))

    def test_snapshot_roundtrip_records_scope_and_source(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "fund-map.json"
            mapping = {"BUG": {"cik": 1432353, "series_id": "S000066713", "class_id": "C000214985"}}
            sfi.write_snapshot(mapping, source=sfi.SEC_FUND_SEARCH, transport="sec_series_search", scope="unresolved_exact_search", path=path)
            loaded, payload = sfi.read_snapshot(path)
            self.assertEqual(loaded, mapping)
            self.assertEqual(payload["scope"], "unresolved_exact_search")
            self.assertEqual(payload["source"], sfi.SEC_FUND_SEARCH)

    def test_fetch_remote_retries_http_failure_and_accepts_valid_map(self):
        session = _Session([_Response(error=RuntimeError("HTTP 403")), _Response(payload=_valid_payload())])
        mapping = sfi.fetch_remote(session=session, retries=2, sleep=lambda _: None)
        self.assertEqual(session.calls, 2)
        self.assertEqual(len(mapping), 1000)

    def test_fetch_series_exact_uses_official_fast_search(self):
        session = _Session([_Response(text=_series_html())])
        item = sfi.fetch_series_exact("BUG", session=session, retries=1)
        self.assertEqual(item["class_id"], "C000214985")
        self.assertIn("www.sec.gov/cgi-bin/series?", session.urls[0])
        self.assertIn("ticker=BUG", session.urls[0])

    def test_unresolved_candidates_are_us_missing_type_only(self):
        rows = [
            {"ticker": "BUG", "quote_type": None, "region": "United States"},
            {"ticker": "CHAT", "quote_type": "ETF", "region": "United States"},
            {"ticker": "BT.A.L", "quote_type": None, "region": "United Kingdom"},
        ]
        self.assertEqual(sfi.unresolved_series_candidates(rows), ["BUG"])

    def test_refresh_falls_back_from_bulk_to_series_exact_search(self):
        rows = {"stocks": [{"ticker": "BUG", "quote_type": None, "region": "United States"}]}
        mapping = {"BUG": {"cik": 1432353, "series_id": "S000066713", "class_id": "C000214985"}}
        with tempfile.TemporaryDirectory() as td:
            stocks = Path(td) / "stocks.json"
            stocks.write_text(json.dumps(rows), encoding="utf-8")
            with mock.patch.object(sfi, "fetch_remote", side_effect=RuntimeError("HTTP 403")), \
                 mock.patch.object(sfi, "fetch_series_exact", return_value=mapping["BUG"]), \
                 mock.patch.object(sfi, "resolve_via_series", return_value=(mapping, {"attempted": 1, "matched": 1, "errors": 0, "error_examples": []})), \
                 mock.patch.object(sfi, "write_snapshot") as write_snapshot:
                resolved, meta = sfi.refresh_snapshot(stocks_path=stocks)
        self.assertEqual(resolved, mapping)
        self.assertEqual(meta["state"], "remote_series_search")
        self.assertEqual(meta["source"], sfi.SEC_FUND_SEARCH)
        write_snapshot.assert_called_once()

    def test_audit_separates_unresolved_and_explicit_conflicts(self):
        with tempfile.TemporaryDirectory() as td:
            stocks = Path(td) / "stocks.json"
            stocks.write_text(json.dumps({"stocks": [
                {"ticker": "BUG", "quote_type": None, "region": "United States"},
                {"ticker": "CHAT", "quote_type": "ETF", "region": "United States"},
                {"ticker": "ODD", "quote_type": "EQUITY", "region": "United States"},
            ]}), encoding="utf-8")
            old_audit = sfi.AUDIT_PATH
            try:
                sfi.AUDIT_PATH = Path(td) / "audit.json"
                audit = sfi.build_audit(
                    {"BUG": {"cik": 1}, "CHAT": {"cik": 2}, "ODD": {"cik": 3}},
                    {"state": "test", "source": sfi.SEC_FUND_SEARCH, "scope": "test"},
                    stocks_path=stocks,
                )
            finally:
                sfi.AUDIT_PATH = old_audit
            self.assertEqual(audit["unresolved_rows_confirmed_as_registered_funds"], 1)
            self.assertEqual(audit["explicit_non_equity_rows_confirmed"], 1)
            self.assertEqual(audit["explicit_equity_type_conflicts"], 1)


if __name__ == "__main__":
    unittest.main()
