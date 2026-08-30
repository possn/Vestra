from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class MarketLoaderInvariantTests(unittest.TestCase):
    def test_base_bundle_precedes_static_market_modules(self):
        index = read("index.html")
        self.assertLess(index.index('src="app-utils.js'), index.index('src="app.js'))
        self.assertLess(index.index('src="app.js'), index.index('src="market.js'))
        self.assertLess(index.index('src="market.js'), index.index('src="market-data-loader.js'))
        self.assertLess(index.index('src="market-data-loader.js'), index.index('src="politicians.js'))
        self.assertNotIn('src="market-hotfix.js', index)

    def test_static_market_bundle_does_not_reload_base_utils(self):
        index = read("index.html")
        self.assertEqual(index.count('src="app-utils.js'), 1)
        self.assertIn('market-data-loader.js?v=2.2', index)
        self.assertIn('portfolio-sheet-navigation.js?v=1.3', index)

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
        self.assertNotIn("stocks.json?full=1", loader)
        self.assertIn("version:'2.2'", loader)
        self.assertIn("const result=rawOpen(ticker);", loader)
        self.assertIn("hydrateOpenDossier(ticker);", loader)

    def test_dossier_opening_delegates_to_canonical_navigation(self):
        loader = read("market-data-loader.js")
        self.assertIn("function openDossier", loader)
        self.assertIn("window.VestraNavigation", loader)
        self.assertIn("nav?.openCompany", loader)
        self.assertIn("openDossier(ticker,{sourceNode:row})", loader)
        self.assertIn("openDossier(ticker,{origin:'market',sourceNode:jump})", loader)

    def test_dossier_hydration_never_downloads_full_market_payload(self):
        loader = read("market-data-loader.js")
        self.assertNotIn("stocks.json?full=1", loader)
        self.assertIn("The startup index is a valid fallback", loader)
        self.assertIn("tickerHydrationCache", loader)

    def test_politicians_loader_matches_canonical_module_version(self):
        index = read("index.html")
        politicians = read("politicians.js")
        self.assertIn("const VERSION='2.1';", politicians)
        self.assertIn("politicians.js?v=2.1", index)
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
