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
        if url not in self.pages:
            raise RuntimeError(f"missing fake page {url}")
        return self.pages[url]


class LseIdentityTests(unittest.TestCase):
    def setUp(self):
        mod._CACHE = None
        mod._LAST_DIAGNOSTICS.clear()

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

    def test_discovery_scans_current_pages_and_json_embedded_urls(self):
        pages = {page: FakeResponse(text="") for page in mod.LSE_DISCOVERY_PAGES}
        setsqx = mod.LSE_DISCOVERY_PAGES[1]
        reports = mod.LSE_DISCOVERY_PAGES[2]
        pages[setsqx] = FakeResponse(text=(
            '<a href="https://docs.londonstockexchange.com/sites/default/files/setsqx-securities.xlsx">List</a>'
            '<a href="/files/business-parameters.xlsx">Business parameters</a>'
        ))
        pages[reports] = FakeResponse(text=(
            '{"downloadUrl":"https:\/\/docs.londonstockexchange.com\/sites\/default\/files\/instrument-list.xlsx"}'
        ))
        urls = mod._discover_workbook_urls(FakeSession(pages))
        self.assertEqual(urls, [
            "https://docs.londonstockexchange.com/sites/default/files/setsqx-securities.xlsx",
            "https://docs.londonstockexchange.com/sites/default/files/instrument-list.xlsx",
        ])
        self.assertEqual(mod.diagnostics()["pages_ok"], len(mod.LSE_DISCOVERY_PAGES))
        self.assertEqual(mod.diagnostics()["workbooks_discovered"], 2)

    def test_non_lse_downloads_are_rejected(self):
        page = mod.LSE_DISCOVERY_PAGES[0]
        html = '<a href="https://example.com/sets-securities.xlsx">bad</a>'
        self.assertEqual(mod._candidate_downloads(page, html), [])

    def test_all_page_failures_degrade_to_empty_map(self):
        pages = {page: FakeResponse(status=503) for page in mod.LSE_DISCOVERY_PAGES}
        self.assertEqual(mod.build_map(FakeSession(pages)), {})
        self.assertEqual(mod.diagnostics()["pages_ok"], 0)
        self.assertEqual(mod.diagnostics()["workbooks_discovered"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
