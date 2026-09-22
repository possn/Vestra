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
        self.assertLess(index.index('src="app.js'), index.index('src="market-runtime-loader.js'))
        self.assertNotIn('src="market-data-loader.js', index)
        self.assertNotIn('src="politicians.js', index)
        self.assertNotIn('src="market.js', index)
        self.assertNotIn('src="market-hotfix.js', index)

    def test_static_market_bundle_does_not_reload_base_utils(self):
        index = read("index.html")
        self.assertEqual(index.count('src="app-utils.js'), 1)
        runtime_loader = read("market-runtime-loader.js")
        self.assertIn('market-data-loader.js?v=2.6', runtime_loader)
        self.assertNotIn('src="portfolio-sheet-navigation.js', index)
        self.assertIn('portfolio-sheet-navigation.js?v=1.5', runtime_loader)

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
        self.assertIn("version:'2.6'", loader)
        self.assertIn("const result=rawOpen(ticker);", loader)
        self.assertIn("hydrateOpenDossier(ticker);", loader)

    def test_market_only_companions_are_deferred_until_market_load(self):
        universe = read("market-static-universe.js")
        index = read("index.html")
        tail = universe[universe.index("// Dashboard/mobile companions remain eager"):]
        self.assertNotIn("ensureEtfIntelligence();", tail)
        self.assertNotIn("ensureScannerCompanion();", tail)
        self.assertNotIn("ensureAnalysisToolsRuntime();", tail)
        self.assertNotIn("ensureMarketUiPolish();", tail)
        self.assertNotIn("ensureMetalsCompanion();", tail)
        self.assertNotIn("ensureOpportunitySuite();", tail)
        self.assertIn("ensureDashboardMarketSentiment();", tail)
        self.assertNotIn('src="market-metals.js', index)
        self.assertNotIn('src="market-opportunities.js', index)
        self.assertNotIn('src="market-opportunity-lenses.js', index)
        self.assertIn("market-metals.js?v=1.2", universe)
        self.assertIn("market-opportunities.js?v=1.2", universe)
        self.assertIn("market-opportunity-lenses.js?v=3.1", universe)
        self.assertIn("const etfReady = ensureMarketCompanions();", universe)
        self.assertIn("await etfReady;", universe)
        self.assertIn("market-static-universe.js?v=1.18", index)

    def test_dossier_hydration_requires_exact_ticker_identity(self):
        loader = read("market-data-loader.js")
        self.assertIn("shard=txt(manifest[key])", loader)
        self.assertIn("const full=rows[key]", loader)
        self.assertIn("ticker sem shard exato", loader)
        self.assertIn("ticker exato ausente no shard", loader)
        self.assertNotIn("Object.keys(manifest).find", loader)
        self.assertNotIn("Object.keys(rows).find", loader)
        self.assertNotIn("replace(/\\.[A-Z]+$/,'')", loader)

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
        self.assertIn("await hydrateTicker(ticker)", block)
        self.assertNotIn("tickers.map(hydrateTicker)", block)

    def test_dossier_opening_delegates_to_canonical_navigation(self):
        loader = read("market-data-loader.js")
        start = loader.index("function openDossier")
        end = loader.index("\n  document.addEventListener('click'", start)
        block = loader[start:end]
        self.assertIn("window.VestraNavigation", block)
        self.assertIn("nav?.openCompany", block)
        self.assertIn("if(!nav?.openCompany) return Promise.resolve(false)", block)
        self.assertNotIn("VestraMarket?.openTicker", block)
        self.assertNotIn("hydrateOpenDossier(tk)", block)
        self.assertIn("openDossier(ticker,{sourceNode:row})", loader)
        self.assertIn("openDossier(ticker,{origin:'market',sourceNode:jump})", loader)

    def test_dossier_hydration_never_downloads_full_market_payload(self):
        loader = read("market-data-loader.js")
        self.assertNotIn("stocks.json?full=1", loader)
        self.assertIn("The startup index is a valid fallback", loader)
        self.assertIn("tickerHydrationCache", loader)

    def test_dossier_performance_is_local_read_only_diagnostics(self):
        loader = read("market-data-loader.js")
        self.assertIn("dossierPerf", loader)
        self.assertIn("markDossierOpen", loader)
        self.assertIn("sheetMs", loader)
        self.assertIn("hydrationMs", loader)
        self.assertIn("performance:()=>dossierPerf.map", loader)
        self.assertIn("if(dossierPerf.length>20)", loader)
        self.assertNotIn("sendBeacon", loader)
        self.assertNotIn("/telemetry", loader)

    def test_politicians_loader_matches_canonical_module_version(self):
        index = read("index.html")
        politicians = read("politicians.js")
        self.assertIn("const VERSION='2.1';", politicians)
        universe = read("market-static-universe.js")
        self.assertNotIn('src="politicians.js', index)
        self.assertIn("politicians.js?v=2.1", universe)
        self.assertIn("ensurePoliticiansCompanion", universe)
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
        self.assertNotIn("const TRUMP", politicians)
        self.assertNotIn("TRUMP_TRADES", politicians)


if __name__ == "__main__":
    unittest.main(verbosity=2)
