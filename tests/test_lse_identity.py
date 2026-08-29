import io
import unittest

import pandas as pd

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

    def _xlsx(self, rows):
        buf = io.BytesIO()
        pd.DataFrame(rows).to_excel(buf, index=False)
        return buf.getvalue()

    def test_exact_tidm_to_isin_mapping_from_official_workbook(self):
        page = mod.LSE_SECURITIES_PAGE
        xlsx = "https://www.londonstockexchange.com/files/list-of-sets-securities.xlsx"
        html = f'<a href="{xlsx}">List of securities available on SETS</a>'
        session = FakeSession({
            page: FakeResponse(text=html),
            xlsx: FakeResponse(content=self._xlsx([
                {"TIDM": "LSEG", "ISIN": "GB00B0SWJX34"},
                {"TIDM": "SSE", "ISIN": "GB0007908733"},
            ])),
        })
        mapping = mod.build_map(session)
        self.assertEqual(mapping["LSEG"], "GB00B0SWJX34")
        self.assertEqual(mapping["SSE"], "GB0007908733")

    def test_ambiguous_tidm_is_discarded(self):
        page = mod.LSE_SECURITIES_PAGE
        xlsx = "https://www.londonstockexchange.com/files/setsqx-securities.xlsx"
        html = f'<a href="{xlsx}">SETSqx</a>'
        session = FakeSession({
            page: FakeResponse(text=html),
            xlsx: FakeResponse(content=self._xlsx([
                {"Tradable Instrument Display Mnemonic": "TEST", "ISIN Code": "GB0000000001"},
                {"Tradable Instrument Display Mnemonic": "TEST", "ISIN Code": "GB0000000002"},
            ])),
        })
        self.assertNotIn("TEST", mod.build_map(session))

    def test_resolver_is_london_only_and_supports_share_class_punctuation(self):
        mod._CACHE = {"BT.A": "GB0030913577"}
        self.assertEqual(mod.resolve_isin("BT-A.L"), "GB0030913577")
        self.assertEqual(mod.resolve_isin("BT.A.L"), "GB0030913577")
        self.assertIsNone(mod.resolve_isin("BT-A"))
        self.assertIsNone(mod.resolve_isin("ABC.DE"))

    def test_unrelated_workbooks_are_not_downloaded(self):
        page = mod.LSE_SECURITIES_PAGE
        html = (
            '<a href="/files/sets-securities.xlsx">SETS</a>'
            '<a href="/files/business-parameters.xlsx">Business parameters</a>'
        )
        session = FakeSession({page: FakeResponse(text=html)})
        urls = mod._discover_workbook_urls(session)
        self.assertEqual(urls, ["https://www.londonstockexchange.com/files/sets-securities.xlsx"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
