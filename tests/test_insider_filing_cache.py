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
  <issuer><issuerCik>0000320193</issuerCik><issuerName>Example Corporation</issuerName></issuer>
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
            "issuer_cik": "0000320193",
            "accession": filing["accession"],
            "filing_date": filing["filing_date"],
            "raw_nonderivative_transactions": 1,
            "transactions": [{"ticker": "OLD", "issuer_cik": "0000320193", "accession": filing["accession"], "type": "buy", "value": 200.0}],
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

    def test_issuer_cik_mismatch_is_not_attributed_to_requested_ticker(self):
        filing = self.filing("0001-26-000010")
        wrong = VALID_XML.replace(b"0000320193", b"0000000042")
        with mock.patch.object(insiders, "_get", return_value=FakeResponse(wrong)):
            tx, raw_count, detail = insiders._fetch_structured_filing(
                "0000320193", filing, "AAPL")
        self.assertEqual((tx, raw_count), ([], 0))
        self.assertIn("issuer_cik_missing_or_mismatched", detail)
        self.assertNotIn(insiders._cache_key("0000320193", filing["accession"]), insiders._filing_cache)

    def test_missing_issuer_cik_is_not_a_confirmed_insider_buy(self):
        filing = self.filing("0001-26-000011")
        missing = VALID_XML.replace(
            b"<issuer><issuerCik>0000320193</issuerCik><issuerName>Example Corporation</issuerName></issuer>",
            b"")
        with mock.patch.object(insiders, "_get", return_value=FakeResponse(missing)):
            tx, raw_count, detail = insiders._fetch_structured_filing(
                "0000320193", filing, "AAPL")
        self.assertEqual((tx, raw_count), ([], 0))
        self.assertIn("issuer_cik_missing_or_mismatched", detail)

    def test_unverified_legacy_cache_does_not_bypass_xml_identity(self):
        filing = self.filing("0001-26-000012")
        insiders._filing_cache[insiders._cache_key("320193", filing["accession"])] = {
            "cik": "320193", "accession": filing["accession"],
            "raw_nonderivative_transactions": 1,
            "transactions": [{"ticker": "AAPL", "type": "buy", "value": 402660529}],
        }
        self.assertIsNone(insiders._cached_filing("320193", filing, "AAPL"))
        with mock.patch.object(insiders, "_get", return_value=FakeResponse(VALID_XML)):
            tx, raw_count, detail = insiders._fetch_structured_filing("320193", filing, "AAPL")
        self.assertEqual(raw_count, 1)
        self.assertNotEqual(tx[0]["value"], 402660529)
        self.assertEqual(insiders._filing_cache[insiders._cache_key("320193", filing["accession"])]["issuer_cik"], "0000320193")

    def test_multiple_transactions_in_one_filing_are_not_deduplicated_by_accession(self):
        filing = self.filing("0001-26-000013")
        transaction = VALID_XML.split(b"<nonDerivativeTransaction>")[1].split(b"</nonDerivativeTransaction>")[0]
        doubled = VALID_XML.replace(b"</nonDerivativeTable>",
            b"<nonDerivativeTransaction>" + transaction + b"</nonDerivativeTransaction></nonDerivativeTable>")
        with mock.patch.object(insiders, "_get", return_value=FakeResponse(doubled)):
            tx, raw_count, _ = insiders._fetch_structured_filing("320193", filing, "AAPL")
        self.assertEqual((len(tx), raw_count), (2, 2))
        self.assertTrue(all(insiders._same_cik(x["issuer_cik"], "320193") for x in tx))

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


    def test_partial_form4_failure_cannot_publish_zero_as_verified(self):
        import datetime as dt
        today = dt.date.today().isoformat()
        filings = [
            {"accession": "acc1", "filing_date": today},
            {"accession": "acc2", "filing_date": today},
        ]
        good = [{"ticker": "AAPL", "type": "buy", "date": today, "value": 200.0}]
        with mock.patch.object(insiders, "_load_ticker_cik_map", return_value={"AAPL": "320193"}), \
             mock.patch.object(insiders, "_recent_form4_rows", return_value=filings), \
             mock.patch.object(insiders, "_fetch_structured_filing",
                               side_effect=[(good, 1, "file.xml"), ([], 0, "network error")]):
            result = insiders.insider_activity("AAPL")
        self.assertEqual(result["status"], "degraded")
        self.assertEqual(result["reason"], "form4_xml_unavailable")
        self.assertEqual(result["detail_filings_parsed"], 1)
        self.assertIsNone(result["net_value_30d"])
        self.assertIsNone(result["net_value_365d"])

    def test_detail_budget_truncation_is_not_complete_annual_coverage(self):
        import datetime as dt
        today = dt.date.today().isoformat()
        filings = [{"accession": f"acc{i}", "filing_date": today} for i in range(3)]
        with mock.patch.object(insiders, "_load_ticker_cik_map", return_value={"AAPL": "320193"}), \
             mock.patch.object(insiders, "_recent_form4_rows", return_value=filings), \
             mock.patch.object(insiders, "_fetch_structured_filing",
                               return_value=([{"ticker": "AAPL", "type": "buy", "date": today,
                                              "value": 100.0}], 1, "file.xml")):
            result = insiders.insider_activity("AAPL", max_detail_filings=2)
        self.assertEqual(result["status"], "degraded")
        self.assertEqual(result["reason"], "form4_detail_limit")
        self.assertEqual(result["detail_filings_truncated"], 1)
        self.assertIsNone(result["net_value_365d"])

    def test_old_transaction_in_recent_amended_filing_not_counted_as_365d(self):
        import datetime as dt
        today = dt.date.today().isoformat()
        old = (dt.date.today() - dt.timedelta(days=450)).isoformat()
        filings = [{"accession": "amendment", "filing_date": today}]
        transactions = [{"ticker": "AAPL", "type": "buy", "date": old, "value": 90000.0}]
        with mock.patch.object(insiders, "_load_ticker_cik_map", return_value={"AAPL": "320193"}), \
             mock.patch.object(insiders, "_recent_form4_rows", return_value=filings), \
             mock.patch.object(insiders, "_fetch_structured_filing",
                               return_value=(transactions, 1, "amended.xml")):
            result = insiders.insider_activity("AAPL")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["buy_value_365d"], 0.0)
        self.assertEqual(result["transactions_365d"], [])

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
