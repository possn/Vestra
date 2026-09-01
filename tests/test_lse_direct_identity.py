import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import lse_identity


class FakeResponse:
    def __init__(self, payload=None, status=200, text="", content=b""):
        self._payload = payload
        self.status_code = status
        self.ok = 200 <= status < 300
        self.text = text
        self.content = content

    def raise_for_status(self):
        if not self.ok:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.urls = []

    def get(self, url, timeout=25):
        self.urls.append(url)
        if not self.responses:
            raise RuntimeError("no fixture")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class LseDirectIdentityTests(unittest.TestCase):
    def setUp(self):
        lse_identity._DIRECT_CACHE.clear()
        lse_identity._CACHE = None
        lse_identity._LAST_DIAGNOSTICS.clear()

    def test_direct_tidm_endpoint_returns_exact_isin(self):
        session = FakeSession([FakeResponse({
            "tidm": "ANTO",
            "isin": "GB0000456144",
            "currency": "GBX",
        })])
        result = lse_identity.resolve_isin("ANTO.L", session)
        self.assertEqual(result, "GB0000456144")
        self.assertEqual(
            session.urls,
            [f"{lse_identity.LSE_INSTRUMENT_ENDPOINT}/ANTO"],
        )
        self.assertEqual(lse_identity.diagnostics().get("direct_hits"), 1)

    def test_direct_success_does_not_enumerate_workbooks(self):
        session = FakeSession([FakeResponse({"tidm": "LSEG", "isin": "GB00B0SWJX34"})])
        self.assertEqual(lse_identity.resolve_isin("LSEG.L", session), "GB00B0SWJX34")
        self.assertEqual(len(session.urls), 1)
        self.assertNotIn("workbooks_discovered", lse_identity.diagnostics())

    def test_mismatched_returned_tidm_is_rejected(self):
        session = FakeSession([FakeResponse({"tidm": "SHEL", "isin": "GB00BP6MXD84"})])
        # If the direct identity is rejected the compatibility workbook path is
        # attempted. Supply five empty discovery pages so it resolves to None.
        session.responses.extend([FakeResponse(text="") for _ in lse_identity.LSE_DISCOVERY_PAGES])
        self.assertIsNone(lse_identity.resolve_isin("BP.L", session))

    def test_invalid_isin_is_rejected(self):
        session = FakeSession([FakeResponse({"tidm": "SHEL", "isin": "NOT-AN-ISIN"})])
        session.responses.extend([FakeResponse(text="") for _ in lse_identity.LSE_DISCOVERY_PAGES])
        self.assertIsNone(lse_identity.resolve_isin("SHEL.L", session))

    def test_non_london_ticker_never_calls_lse(self):
        session = FakeSession([])
        self.assertIsNone(lse_identity.resolve_isin("MSFT", session))
        self.assertEqual(session.urls, [])

    def test_direct_result_is_cached_per_tidm(self):
        session = FakeSession([FakeResponse({"tidm": "ANTO", "isin": "GB0000456144"})])
        self.assertEqual(lse_identity.resolve_isin("ANTO.L", session), "GB0000456144")
        self.assertEqual(lse_identity.resolve_isin("ANTO.L", session), "GB0000456144")
        self.assertEqual(len(session.urls), 1)

    def test_class_punctuation_fallback_is_exact_and_conflict_fails_closed(self):
        session = FakeSession([
            FakeResponse(status=404),
            FakeResponse({"tidm": "ABC.X", "isin": "GB0000000001"}),
        ])
        # First candidate ABC-X fails; exact punctuation alternative ABC.X works.
        self.assertEqual(lse_identity._resolve_direct("ABC-X.L", session), "GB0000000001")

        lse_identity._DIRECT_CACHE.clear()
        conflict = FakeSession([
            FakeResponse({"tidm": "ABC-X", "isin": "GB0000000001"}),
            FakeResponse({"tidm": "ABC.X", "isin": "GB0000000019"}),
        ])
        self.assertIsNone(lse_identity._resolve_direct("ABC-X.L", conflict))
        self.assertEqual(lse_identity.diagnostics().get("direct_ambiguous"), 1)


if __name__ == "__main__":
    unittest.main()
