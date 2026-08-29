import unittest

from scripts import lse_identity as mod


class FakeResponse:
    def __init__(self, text="", content=b"", status=200):
        self.text = text
        self.content = content
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self, pages):
        self.pages = pages

    def get(self, url, timeout=None):
        return self.pages[url]


class LseIdentityTests(unittest.TestCase):
    def setUp(self):
        mod._CACHE = None

    def test_column_detection_accepts_official_lse_labels(self):
        self.assertEqual(mod._pick_columns(["TIDM", "ISIN"]), ("TIDM", "ISIN"))
        self.assertEqual(
            mod._pick_columns(["Tradable Instrument Display Mnemonic", "ISIN Code"]),
            ("Tradable Instrument Display Mnemonic", "ISIN Code"),
        )

    def test_resolver_is_london_only_and_supports_share_class_punctuation(self):
        mod._CACHE = {"BT.A": "GB0030913577", "LSEG": "GB00B0SWJX34"}
        self.assertEqual(mod.resolve_isin("BT-A.L"), "GB0030913577")
        self.assertEqual(mod.resolve_isin("BT.A.L"), "GB0030913577")
        self.assertEqual(mod.resolve_isin("LSEG.L"), "GB00B0SWJX34")
        self.assertIsNone(mod.resolve_isin("BT-A"))
        self.assertIsNone(mod.resolve_isin("ABC.DE"))

    def test_conflicting_exact_candidates_are_rejected(self):
        mod._CACHE = {
            "BT-A": "GB0000000001",
            "BT.A": "GB0000000002",
        }
        self.assertIsNone(mod.resolve_isin("BT-A.L"))

    def test_unrelated_workbooks_are_not_downloaded(self):
        page = mod.LSE_SECURITIES_PAGE
        html = (
            '<a href="/files/sets-securities.xlsx">SETS</a>'
            '<a href="/files/business-parameters.xlsx">Business parameters</a>'
        )
        session = FakeSession({page: FakeResponse(text=html)})
        urls = mod._discover_workbook_urls(session)
        self.assertEqual(urls, ["https://www.londonstockexchange.com/files/sets-securities.xlsx"])

    def test_page_failure_degrades_to_empty_map(self):
        page = mod.LSE_SECURITIES_PAGE
        session = FakeSession({page: FakeResponse(status=503)})
        self.assertEqual(mod.build_map(session), {})


if __name__ == "__main__":
    unittest.main(verbosity=2)
