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
        self.assertIn("market-data-loader.js?v=2.0", hotfix)

    def test_market_loading_is_native_and_loader_only_hydrates_dossiers(self):
        market = read("market.js")
        loader = read("market-data-loader.js")
        start = market.index("async function ensureLoaded")
        end = market.index("\n  function ", start)
        block = market[start:end]
        self.assertIn("stocks-index.json", block)
        self.assertLess(block.index("stocks-index.json"), block.index("stocks.json"))
        self.assertNotIn("window.fetch =", loader)
        self.assertNotIn("indexPayloadPromise", loader)
        self.assertNotIn("sharedIndexPayload", loader)
        self.assertIn("dossiers-manifest.json", loader)
        self.assertIn("data/dossiers/", loader)
        self.assertIn("stocks.json?full=1", loader)
        self.assertIn("version:'2.0'", loader)

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

    def test_trump_is_restored_through_executive_disclosures_not_inline_trade_hardcode(self):
        executives = read("data/executives.json")
        politicians = read("politicians.js")
        self.assertIn('"key": "executive:donald-trump"', executives)
        self.assertIn('"name": "Donald J. Trump"', executives)
        self.assertIn('OGE Form 278-T', executives)
        self.assertIn("data/executives.json", politicians)
        self.assertNotIn("const TRUMP", politicians)
        self.assertNotIn("TRUMP_TRADES", politicians)


if __name__ == "__main__":
    unittest.main(verbosity=2)
