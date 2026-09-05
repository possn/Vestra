from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


class NativeMarketLoadingTests(unittest.TestCase):
    def test_market_base_prefers_columnar_then_index_then_legacy_fallback(self):
        market = read('market.js')
        universe = read('market-static-universe.js')
        self.assertIn('VestraMarketStaticUniverse', market)
        self.assertIn('staticUniverse?.ensureLoaded', market)
        self.assertIn("['data/stocks-startup.json', true]", universe)
        self.assertIn("['data/stocks-index.json', false]", universe)
        self.assertIn("['data/stocks.json', false]", universe)
        self.assertLess(universe.index('stocks-startup.json'), universe.index('stocks-index.json'))
        self.assertLess(universe.index('stocks-index.json'), universe.index('stocks.json'))
        self.assertIn("cache: 'no-store'", universe)
        self.assertIn('unpackStartupPayload', universe)

    def test_lazy_loader_never_monkeypatches_window_fetch(self):
        loader = read('market-data-loader.js')
        self.assertNotIn('window.fetch =', loader)
        self.assertNotIn('sharedIndexPayload', loader)
        self.assertNotIn('requestUrl(', loader)
        self.assertIn("version:'2.5'", loader)
        self.assertIn('dossiers-manifest.json', loader)
        self.assertIn('data/dossiers/', loader)
        self.assertNotIn('data/stocks.json?full=1', loader)
        self.assertIn('window.VestraNavigation', loader)
        self.assertIn('openDossier', loader)
        self.assertIn('hydrateOpenDossier', loader)

    def test_static_universe_is_the_canonical_market_index_owner(self):
        universe = read('market-static-universe.js')
        self.assertIn('stocks-startup.json', universe)
        self.assertIn('stocks-index.json', universe)
        self.assertIn('stocks.json', universe)
        self.assertIn('getStocks', universe)
        self.assertIn('loadFirstAvailable', universe)
        self.assertNotIn('window.fetch =', universe)

    def test_shared_market_state_consumers_do_not_refetch_universe(self):
        brief = read('market-company-brief.js')
        self.assertIn('window.VestraMarket', brief)
        self.assertIn('resolvePortfolioStock', brief)
        self.assertNotIn("fetch('./data/stocks-index.json'", brief)
        self.assertNotIn("fetch('./data/stocks.json'", brief)
        self.assertIn('new MutationObserver', brief)

        opportunities = read('market-opportunities.js')
        self.assertIn('window.VestraMarketStaticUniverse', opportunities)
        self.assertIn('getStocks', opportunities)
        self.assertNotIn("fetch('./data/stocks-index.json'", opportunities)
        self.assertNotIn("fetch('./data/stocks.json'", opportunities)
        self.assertIn('new MutationObserver', opportunities)

        swap = read('vestra-swap-lab.js')
        self.assertIn('window.VestraMarketStaticUniverse', swap)
        self.assertIn('getStocks', swap)
        self.assertNotIn("fetch('./data/stocks-index.json'", swap)
        self.assertNotIn("fetch('./data/stocks.json'", swap)
        self.assertNotIn('function load()', swap)
        self.assertIn('new MutationObserver', swap)

        ai = read('vestra-ai-brief.js')
        self.assertIn('window.VestraMarketStaticUniverse', ai)
        self.assertIn('getStocks', ai)
        self.assertNotIn("fetch('./data/stocks-index.json'", ai)
        self.assertNotIn("fetch('./data/stocks.json'", ai)
        self.assertNotIn('function load()', ai)
        self.assertIn('new MutationObserver', ai)

    def test_service_worker_matches_native_market_generation(self):
        sw = read('sw.js')
        self.assertIn('Vestra Service Worker v10.12', sw)
        self.assertIn('vestra-cache-v126', sw)
        self.assertIn('./market-live-overlay.js', sw)
        self.assertIn('./market-static-universe.js', sw)
        self.assertIn('./market-data-loader.js', sw)
        self.assertIn('./market-company-brief.js', sw)
        self.assertIn('./portfolio-card-classifier.js', sw)
        self.assertIn('./market-opportunities.js', sw)
        self.assertIn('./vestra-portfolio-hierarchy.js', sw)
        self.assertIn('./vestra-swap-lab.js', sw)
        self.assertIn('./portfolio-diagnostics.js', sw)
        self.assertIn('./vestra-ai-brief.js', sw)
        self.assertIn('./portfolio-dossier-routing.js', sw)


if __name__ == '__main__':
    unittest.main(verbosity=2)
