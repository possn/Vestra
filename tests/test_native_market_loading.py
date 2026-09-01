from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


class NativeMarketLoadingTests(unittest.TestCase):
    def test_market_base_loads_light_index_before_legacy_fallback(self):
        market = read('market.js')
        universe = read('market-static-universe.js')
        self.assertIn('VestraMarketStaticUniverse', market)
        self.assertIn('staticUniverse?.ensureLoaded', market)
        self.assertIn("fetchImpl('data/stocks-index.json'", universe)
        self.assertIn("fetchImpl('data/stocks.json'", universe)
        self.assertLess(universe.index('stocks-index.json'), universe.index('stocks.json'))
        self.assertIn("cache: 'no-store'", universe)

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

    def test_runtime_market_consumers_are_index_first(self):
        for path in (
            'market-opportunities.js',
            'market-company-brief.js',
            'vestra-swap-lab.js',
            'vestra-ai-brief.js',
        ):
            source = read(path)
            self.assertIn('stocks-index.json', source, path)
            self.assertIn('stocks.json', source, path)
            self.assertLess(source.index('stocks-index.json'), source.index('stocks.json'), path)

    def test_service_worker_matches_native_market_generation(self):
        sw = read('sw.js')
        self.assertIn('Vestra Service Worker v10.11', sw)
        self.assertIn('vestra-cache-v125', sw)
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
