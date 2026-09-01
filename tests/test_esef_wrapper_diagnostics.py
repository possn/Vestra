import pathlib
import sys
import types
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

# Architecture CI intentionally does not install the heavy market-data
# dependencies. Stub only the import-time module names; the production enrich
# function is patched in these unit tests, so no requests/yfinance API is used.
sys.modules.setdefault("requests", types.ModuleType("requests"))
sys.modules.setdefault("yfinance", types.ModuleType("yfinance"))

import esef_enrich


class ESEFWrapperDiagnosticsTests(unittest.TestCase):
    def test_wrapper_logs_existing_lse_diagnostics_without_extra_retrieval(self):
        raw = [object()]
        expected = [object()]
        diag = {"direct_requests": 3, "direct_failures": 2, "direct_hits": 1}

        with patch.object(esef_enrich, "_enrich_esef", return_value=expected) as enrich_mock, \
             patch.object(esef_enrich, "_lse_diagnostics", return_value=diag), \
             self.assertLogs("esef_enrich", level="INFO") as logs:
            result = esef_enrich.enrich(raw, priority=["vod.l"], max_nonpriority=7)

        self.assertIs(result, expected)
        enrich_mock.assert_called_once_with(raw, priority={"VOD.L"}, max_nonpriority=7)
        self.assertTrue(any("direct_requests" in line and "direct_hits" in line for line in logs.output))

    def test_wrapper_reports_when_no_lse_identity_request_was_recorded(self):
        with patch.object(esef_enrich, "_enrich_esef", return_value=[]), \
             patch.object(esef_enrich, "_lse_diagnostics", return_value={}), \
             self.assertLogs("esef_enrich", level="INFO") as logs:
            result = esef_enrich.enrich([])

        self.assertEqual(result, [])
        self.assertTrue(any("no LSE identity requests recorded" in line for line in logs.output))


if __name__ == "__main__":
    unittest.main()
