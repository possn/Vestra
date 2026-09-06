from pathlib import Path
import re
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
        self.assertIn('market-data-loader.js?v=2.5', index)
        self.assertIn('portfolio-sheet-navigation.js?v=1.3', index)

    def test_market_loading_is_native_and_loader_only_hydrates_dossiers(self):
        market = read("market.js")
        universe = read("market-static-universe.js")
        loader = read("market-data-loader.js")
        self.assertIn("VestraMarketStaticUniverse", market)
        self.assertIn("staticUniverse?.ensureLoaded", market)
        self.assertIn("stocks-startup.json", universe)
        self.assertIn("stocks-index.json", universe)
        candidates_match = re.search(r"const candidates\s*=\s*\[(.*?)\];", universe, re.S)
        self.assertIsNotNone(candidates_match)
        candidates = candidates_match.group(1)
        self.assertLess(candidates.index("stocks-startup.json"), candidates.index("stocks-index.json"))
        self.assertNotIn("stocks.json", candidates, "native browser bootstrap must never include the full market snapshot")
        self.assertIn("cache: 'no-store'", universe)
        self.assertNotIn("window.fetch =", loader)
        self.assertNotIn("indexPayloadPromise", loader)
        self.assertNotIn("sharedIndexPayload", loader)
        self.assertIn("dossiers-manifest.json", loader)
        self.assertIn("data/dossiers/", loader)
        self.assertNotIn("stocks.json?full=1", loader)
        self.assertIn("version:'2.5'", loader)
        self.assertIn("const result=rawOpen(ticker);", loader)
        self.assertIn("hydrateOpenDossier(ticker);", loader)

    def test_portfolio_tool_opens_before_background_hydration(self):
        loader = read("market-data-loader.js")
        start = loader.index("const portfolio=e.target.closest?.('[data-market-tool=\"portfolio\"]')")
        end = loader.index("\n    }", start) + len("\n    }")
        block = loader[start:end]
        self.assertIn("portfolio.click()", block)
        self.assertIn("hydratePortfolio().catch(()=>{})", block)
        self.assertLess(block.index("portfolio.click()"), block.index("hydratePortfolio().catch(()=>{})"))
        self.assertNotIn("hydratePortfolio().finally", block)

    def test_portfolio_background_hydration_is_bounded(self):
        loader = read("market-data-loader.js")
        start = loader.index("async function hydratePortfolio()")
        end = loader.index("\n  function installApiWrapper", start)
        block = loader[start:end]
        self.assertIn("const workerCount=Math.min(2,queue.length)", block)
        self.assertIn("await Promise.all(Array.from({length:workerCount},worker))", block)
        self.assertNotIn("Promise.all(tickers.map", block)

    def test_portfolio_background_hydration_is_only_for_visible_holdings(self):
        loader = read("market-data-loader.js")
        start = loader.index("async function hydratePortfolio()")
        end = loader.index("\n  function installApiWrapper", start)
        block = loader[start:end]
        self.assertIn("collectPortfolioTickers", block)
        self.assertNotIn("M.stocks.map", block)

    def test_dossier_hydration_never_downloads_full_market_payload(self):
        loader = read("market-data-loader.js")
        self.assertNotIn("data/stocks.json", loader)
        self.assertNotIn("stocks.json?full=1", loader)
        self.assertIn("dossiers-manifest.json", loader)
        self.assertIn("data/dossiers/", loader)

    def test_dossier_opening_delegates_to_canonical_navigation(self):
        loader = read("market-data-loader.js")
        self.assertIn("const result=rawOpen(ticker);", loader)
        self.assertIn("hydrateOpenDossier(ticker);", loader)
        self.assertLess(loader.index("const result=rawOpen(ticker);"), loader.index("hydrateOpenDossier(ticker);"))

    def test_dossier_performance_is_local_read_only_diagnostics(self):
        loader = read("market-data-loader.js")
        self.assertIn("performance", loader)
        self.assertNotIn("sendBeacon", loader)
        self.assertNotIn("/analytics", loader)

    def test_politicians_loader_matches_canonical_module_version(self):
        index = read("index.html")
        self.assertIn('politicians.js?v=2.6', index)

    def test_trump_is_restored_through_executive_disclosures_not_inline_trade_hardcode(self):
        politicians = read("politicians.js")
        self.assertIn("executives.json", politicians)
        self.assertNotIn("Donald J. Trump", politicians)


if __name__ == "__main__":
    unittest.main(verbosity=2)
