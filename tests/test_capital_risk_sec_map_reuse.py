import sys
import types
import unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

if "requests" not in sys.modules:
    requests_stub = types.ModuleType("requests")
    requests_stub.Session = object
    sys.modules["requests"] = requests_stub

import capital_risk


class Row:
    def __init__(self, ticker="AAPL", quote_type="EQUITY"):
        self.ticker = ticker
        self.quote_type = quote_type
        self.current_price = 100.0
        self.market_cap = 3_000_000_000_000
        self.diluted_shares_yoy = None
        self.free_cash_flow = None


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self):
        self.headers = {}
        self.urls = []

    def get(self, url, timeout=18):
        self.urls.append((url, timeout))
        return FakeResponse({"filings": {"recent": {}}})


class CapitalRiskSecMapReuseTests(unittest.TestCase):
    def test_enrich_uses_shared_validated_ticker_map_not_direct_catalog_get(self):
        row = Row()
        session = FakeSession()
        with mock.patch.object(capital_risk.requests, "Session", return_value=session), \
             mock.patch.object(capital_risk, "_load_ticker_map", return_value={"AAPL": 320193}) as load_map, \
             mock.patch.object(capital_risk, "_scan_docs", return_value={
                 "capital_structure_flags": [],
                 "capital_structure_risk": "clear",
                 "reverse_split_count_24m": 0,
                 "reverse_split_latest_date": None,
                 "capital_risk_filings_checked": 0,
             }), \
             mock.patch.object(capital_risk.time, "sleep", return_value=None):
            result = capital_risk.enrich([row], priority={"AAPL"})

        self.assertIs(result[0], row)
        load_map.assert_called_once_with(session)
        self.assertTrue(row.capital_risk_checked)
        self.assertEqual(len(session.urls), 1)
        self.assertEqual(
            session.urls[0][0],
            "https://data.sec.gov/submissions/CIK0000320193.json",
        )
        self.assertFalse(any("/files/company_tickers" in url for url, _ in session.urls))

    def test_map_failure_preserves_rows_without_downstream_requests(self):
        row = Row()
        session = FakeSession()
        with mock.patch.object(capital_risk.requests, "Session", return_value=session), \
             mock.patch.object(capital_risk, "_load_ticker_map", side_effect=RuntimeError("no validated map")):
            result = capital_risk.enrich([row], priority={"AAPL"})

        self.assertIs(result[0], row)
        self.assertEqual(session.urls, [])
        self.assertFalse(hasattr(row, "capital_risk_checked"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
