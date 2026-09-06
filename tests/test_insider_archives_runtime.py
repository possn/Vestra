from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import insider_archives_runtime


SAMPLE_SUBMISSION = """
<SEC-DOCUMENT>
<DOCUMENT>
<TYPE>4
<SEQUENCE>1
<FILENAME>ownership.xml
<TEXT>
<XML>
<?xml version="1.0"?>
<ownershipDocument>
  <nonDerivativeTable>
    <nonDerivativeTransaction>
      <transactionCoding><transactionCode>P</transactionCode></transactionCoding>
      <transactionAmounts>
        <transactionShares><value>10</value></transactionShares>
        <transactionPricePerShare><value>12.5</value></transactionPricePerShare>
        <transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode>
      </transactionAmounts>
      <transactionDate><value>2026-09-05</value></transactionDate>
    </nonDerivativeTransaction>
  </nonDerivativeTable>
</ownershipDocument>
</XML>
</TEXT>
</DOCUMENT>
</SEC-DOCUMENT>
"""


class Response:
    text = SAMPLE_SUBMISSION


class Logger:
    def __init__(self):
        self.info_rows = []
        self.warning_rows = []

    def info(self, *args): self.info_rows.append(args)
    def warning(self, *args): self.warning_rows.append(args)


class FakeModule:
    def __init__(self):
        self.log = Logger()
        self.cache = {}
        self.api_calls = 0
        self.archive_calls = 0

    def _recent_form4_rows(self, cik, days):
        self.api_calls += 1
        return [{"filing_date": "2026-09-05", "accession": "api", "primary_document": "api.xml"}]

    def _cached_filing(self, cik, filing, ticker):
        return self.cache.get((cik, filing.get("accession")))

    def _store_cached_filing(self, cik, filing, transactions, raw_count):
        self.cache[(cik, filing.get("accession"))] = (transactions, raw_count, "cache")

    def _get(self, url):
        self.archive_calls += 1
        return Response()

    def _parse_ownership_xml(self, content, ticker, accession):
        text = content.decode("utf-8")
        self.assertions.append((ticker, accession, "ownershipDocument" in text))
        return ([{"ticker": ticker, "accession": accession, "type": "buy"}], 1)

    def _fetch_structured_filing(self, cik, filing, ticker):
        return ([{"ticker": ticker, "accession": "api"}], 1, "api")

    def annotate(self, tickers, pause=0.0):
        filings = self._recent_form4_rows("0000000001", 365)
        result = []
        for filing in filings:
            result.append(self._fetch_structured_filing("0000000001", filing, tickers[0]))
        return result

    assertions = []


class InsiderArchivesRuntimeTests(unittest.TestCase):
    def setUp(self):
        FakeModule.assertions = []

    def test_submission_parser_extracts_only_ownership_document(self):
        xml = insider_archives_runtime._extract_ownership_xml(SAMPLE_SUBMISSION)
        self.assertIsNotNone(xml)
        text = xml.decode("utf-8")
        self.assertIn("<ownershipDocument>", text)
        self.assertNotIn("<SEC-DOCUMENT>", text)

    def test_api_path_is_untouched_without_explicit_probe_block(self):
        module = FakeModule()
        state = insider_archives_runtime.install(module=module, environ={})
        self.assertFalse(state["active"])
        result = module.annotate(["AAA"])
        self.assertEqual(module.api_calls, 1)
        self.assertEqual(result[0][2], "api")

    def test_uniform_403_probe_uses_archive_rows_and_full_submission(self):
        module = FakeModule()
        rows = {
            "0000000001": [{
                "filing_date": "2026-09-05",
                "accession": "0000000001-26-000001",
                "primary_document": "",
                "archive_submission_url": "https://www.sec.gov/Archives/edgar/data/1/one.txt",
            }]
        }
        state = insider_archives_runtime.install(
            module=module,
            environ={"SEC_USER_AGENT": ""},
            row_loader=lambda: (rows, 5),
        )
        result = module.annotate(["AAA"])
        self.assertTrue(state["active"])
        self.assertEqual(state["indexes_loaded"], 5)
        self.assertEqual(module.api_calls, 0)
        self.assertEqual(module.archive_calls, 1)
        self.assertEqual(result[0][0][0]["accession"], "0000000001-26-000001")
        self.assertEqual(FakeModule.assertions[-1], ("AAA", "0000000001-26-000001", True))

    def test_cached_accession_avoids_archive_download(self):
        module = FakeModule()
        accession = "0000000001-26-000001"
        module.cache[("0000000001", accession)] = ([{"ticker": "AAA", "accession": accession}], 1, "cache")
        rows = {"0000000001": [{
            "filing_date": "2026-09-05",
            "accession": accession,
            "primary_document": "",
            "archive_submission_url": "https://www.sec.gov/Archives/edgar/data/1/one.txt",
        }]}
        insider_archives_runtime.install(
            module=module,
            environ={"SEC_USER_AGENT": ""},
            row_loader=lambda: (rows, 5),
        )
        result = module.annotate(["AAA"])
        self.assertEqual(module.api_calls, 0)
        self.assertEqual(module.archive_calls, 0)
        self.assertEqual(result[0][2], "cache")

    def test_failed_archive_discovery_falls_back_to_existing_api_transport(self):
        module = FakeModule()
        state = insider_archives_runtime.install(
            module=module,
            environ={"SEC_USER_AGENT": ""},
            row_loader=lambda: ({}, 0),
        )
        result = module.annotate(["AAA"])
        self.assertTrue(state["fallback_failed"])
        self.assertEqual(module.api_calls, 1)
        self.assertEqual(result[0][2], "api")


if __name__ == "__main__":
    unittest.main(verbosity=2)
