from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class MarketLoaderInvariantTests(unittest.TestCase):
    def test_base_bundle_precedes_market_and_hotfix(self):
        index = read("index.html")
        self.assertLess(index.index('src="app-utils.js'), index.index('src="app.js'))
        self.assertLess(index.index('src="app.js'), index.index('src="market.js'))
        self.assertLess(index.index('src="market.js'), index.index('src="market-hotfix.js'))

    def test_hotfix_does_not_reload_base_utils(self):
        hotfix = read("market-hotfix.js")
        self.assertNotIn("load('./app-utils.js", hotfix)
        self.assertIn("market-data-loader.js?v=1.2", hotfix)

    def test_legacy_stocks_requests_share_one_lightweight_index_payload(self):
        loader = read("market-data-loader.js")
        self.assertIn("let indexPayloadPromise = null;", loader)
        self.assertIn("async function sharedIndexPayload()", loader)
        self.assertIn("if(indexPayloadPromise) return indexPayloadPromise;", loader)
        self.assertIn("stocks-index.json", loader)
        self.assertIn("new Response(body", loader)
        self.assertIn("X-Vestra-Market-Source", loader)
        self.assertIn("stocks.json?full=1", loader)
        self.assertIn("version:'1.2'", loader)

    def test_legacy_full_dataset_is_only_explicit_dossier_emergency_fallback(self):
        loader = read("market-data-loader.js")
        self.assertEqual(loader.count("stocks.json?full=1"), 1)
        self.assertIn("Emergency compatibility fallback", loader)

    def test_politicians_loader_matches_canonical_module_version(self):
        hotfix = read("market-hotfix.js")
        politicians = read("politicians.js")
        self.assertIn("const VERSION='2.1';", politicians)
        self.assertIn("politicians.js?v=2.1", hotfix)
        self.assertIn("data/executives.json", politicians)
        self.assertIn("TOP 10 COMPRAS", politicians)
        self.assertIn("TOP 10 VENDAS", politicians)
        self.assertIn("vestra-politician-favourites-v2", politicians)

    def test_trump_is_restored_through_executive_disclosures_not_congress_hardcode(self):
        executives = read("data/executives.json")
        politicians = read("politicians.js")
        self.assertIn('"key": "executive:donald-trump"', executives)
        self.assertIn('"name": "Donald J. Trump"', executives)
        self.assertIn('OGE Form 278-T', executives)
        self.assertNotIn("const TRUMP", politicians)
        self.assertNotIn("donald-trump", politicians.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
