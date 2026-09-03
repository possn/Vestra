from pathlib import Path
import sys
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

# The lightweight historical CI does not install requests. Provide the minimal
# import surface insiders.py needs; network calls are mocked in every test.
if "requests" not in sys.modules:
    requests = types.ModuleType("requests")
    requests.Session = object
    requests.HTTPError = type("HTTPError", (Exception,), {})
    adapters = types.ModuleType("requests.adapters")
    adapters.HTTPAdapter = object
    requests.adapters = adapters
    sys.modules["requests"] = requests
    sys.modules["requests.adapters"] = adapters
if "urllib3.util.retry" not in sys.modules:
    retry_mod = types.ModuleType("urllib3.util.retry")
    retry_mod.Retry = object
    sys.modules["urllib3.util.retry"] = retry_mod

import insiders


VALID_XML = b"""<?xml version='1.0'?>
<ownershipDocument>
  <reportingOwner>
    <reportingOwnerId><rptOwnerName>Jane Doe</rptOwnerName></reportingOwnerId>
    <reportingOwnerRelationship><isDirector>1</isDirector></reportingOwnerRelationship>
  </reportingOwner>
  <nonDerivativeTable>
    <nonDerivativeTransaction>
      <transactionDate><value>2026-09-01</value></transactionDate>
      <transactionCoding><transactionCode>P</transactionCode></transactionCoding>
      <transactionAmounts>
        <transactionShares><value>10</value></transactionShares>
        <transactionPricePerShare><value>20</value></transactionPricePerShare>
        <transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode>
      </transactionAmounts>
    </nonDerivativeTransaction>
  </nonDerivativeTable>
</ownershipDocument>
"""


class FakeResponse:
    def __init__(self, content, status_code=200):
        self.content = content
        self.status_code = status_code


class InsiderFilingCacheTests(unittest.TestCase):
    def setUp(self):
        insiders._filing_cache = {}
        insiders._cache_dirty = False

    def filing(self, accession="0001-26-000001"):
        return {
            "filing_date": "2026-09-01",
            "accession": accession,
            "primary_document": "xslF345X06/form4.xml",
        }

    def test_cache_hit_reuses_parsed_accession_without_network(self):
        filing = self.filing()
        key = insiders._cache_key("0000320193", filing["accession"])
        insiders._filing_cache[key] = {
            "cik": "0000320193",
            "accession": filing["accession"],
            "filing_date": filing["filing_date"],
            "raw_nonderivative_transactions": 1,
            "transactions": [{"ticker": "OLD", "accession": filing["accession"], "type": "buy", "value": 200.0}],
            "source": "SEC EDGAR Form 4",
        }
        with mock.patch.object(insiders, "_get", side_effect=AssertionError("network must not be called")):
            tx, raw_count, detail = insiders._fetch_structured_filing("0000320193", filing, "AAPL")
        self.assertEqual(raw_count, 1)
        self.assertEqual(detail, "cache")
        self.assertEqual(tx[0]["ticker"], "AAPL")
        self.assertEqual(tx[0]["accession"], filing["accession"])

    def test_successful_structured_parse_is_cached(self):
        filing = self.filing("0001-26-000002")
        with mock.patch.object(insiders, "_get", return_value=FakeResponse(VALID_XML)):
            tx, raw_count, _detail = insiders._fetch_structured_filing("0000320193", filing, "AAPL")
        self.assertEqual(raw_count, 1)
        self.assertEqual(len(tx), 1)
        key = insiders._cache_key("0000320193", filing["accession"])
        cached = insiders._filing_cache[key]
        self.assertEqual(cached["raw_nonderivative_transactions"], 1)
        self.assertEqual(cached["transactions"][0]["value"], 200.0)
        self.assertTrue(insiders._cache_dirty)

    def test_invalid_html_response_is_never_cached(self):
        filing = self.filing("0001-26-000003")
        with mock.patch.object(insiders, "_get", return_value=FakeResponse(b"<html>SEC FORM 4</html>")):
            tx, raw_count, detail = insiders._fetch_structured_filing("0000320193", filing, "AAPL")
        self.assertEqual(tx, [])
        self.assertEqual(raw_count, 0)
        self.assertIn("found 0 transactions", detail)
        key = insiders._cache_key("0000320193", filing["accession"])
        self.assertNotIn(key, insiders._filing_cache)
        self.assertFalse(insiders._cache_dirty)

    def test_cache_key_is_exact_cik_plus_accession(self):
        self.assertNotEqual(
            insiders._cache_key("320193", "0001-26-000001"),
            insiders._cache_key("789019", "0001-26-000001"),
        )
        self.assertEqual(
            insiders._cache_key("0000320193", "0001-26-000001"),
            insiders._cache_key("320193", "0001-26-000001"),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
