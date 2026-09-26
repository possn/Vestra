# CI touch: desktop canvas CSS audit is validated by runtime, architecture, and browser gates.
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

def read(path):
    return (ROOT / path).read_text(encoding="utf-8")

class StaticMarketRuntimeTests(unittest.TestCase):
    def test_index_owns_market_auxiliary_order_with_lazy_core(self):
        index = read("index.html")
        loader = read("market-runtime-loader.js")
        self.assertNotIn('src="market-hotfix.js', index)
        self.assertNotIn('src="market.js', index)
        order = ['market-runtime-loader.js']
        positions = [index.index(f'src="{name}') for name in order]
        self.assertEqual(positions, sorted(positions))
        for name in order:
            self.assertEqual(index.count(f'src="{name}'), 1, name)
        for lazy in (
            'market-live-overlay.js?v=1.2',
            'market-congress-live.js?v=1.0',
            'market-portfolio-context.js?v=1.0',
            'market-watch-snapshots.js?v=1.0',
            'market-dossier-signals.js?v=1.0',
            'market-search-suggestions.js?v=1.2',
            'market-row-ui.js?v=1.0',
            'market-metric-cleanup.js?v=1.2',
            'market-company-brief.js?v=2.1',
            'portfolio-sheet-navigation.js?v=1.5',
            'portfolio-collapsibles.js?v=1.7',
            'portfolio-card-classifier.js?v=1.8',
            'market-data-loader.js?v=2.6',
        ):
            self.assertIn(lazy, loader)
            self.assertNotIn(f'src="{lazy.split("?")[0]}', index)
        self.assertIn("script.src = 'market.js?v=20260925opt7';", loader)
        universe = read("market-static-universe.js")
        self.assertIn("politicians.js?v=2.1", universe)
        self.assertNotIn('src="politicians.js', index)
        self.assertIn("market-metals.js?v=1.2", universe)
        self.assertIn("market-opportunities.js?v=1.2", universe)
        self.assertIn("market-opportunity-lenses.js?v=3.1", universe)
        for module in (
            "vestra-swap-lab.js?v=1.2",
            "vestra-portfolio-ui.js?v=3.1",
            "portfolio-diagnostics.js?v=1.2",
            "portfolio-dossier-routing.js?v=1.5",
            "vestra-portfolio-hierarchy.js?v=2.3",
            "vestra-ai-brief.js?v=1.2",
        ):
            self.assertIn(module, universe)
        for direct in (
            'src="market-metals.js',
            'src="market-opportunities.js',
            'src="market-opportunity-lenses.js',
            'src="vestra-swap-lab.js',
            'src="vestra-portfolio-ui.js',
            'src="portfolio-diagnostics.js',
            'src="portfolio-dossier-routing.js',
            'src="vestra-portfolio-hierarchy.js',
            'src="vestra-ai-brief.js',
        ):
            self.assertNotIn(direct, index)
        self.assertNotIn('portfolio-navigation-fix.js', index)
        self.assertNotIn('market-close-controller.js', index)
        self.assertNotIn('vestra-portfolio-focus.js', universe)

    def test_every_static_market_script_is_deferred(self):
        index = read("index.html")
        for name in ('market-runtime-loader.js',):
            self.assertIn(f'<script defer="" src="{name}', index)
        self.assertNotIn('src="market-data-loader.js', index)
        self.assertNotIn('src="portfolio-sheet-navigation.js', index)

    def test_service_worker_tracks_final_static_runtime(self):
        sw = read("sw.js")
        self.assertIn('Vestra Service Worker v', sw)
        self.assertRegex(sw, r'vestra-cache-v\d+')
        self.assertIn('staleWhileRevalidate', sw)
        self.assertNotIn('./market-hotfix.js', sw)
        self.assertNotIn('./portfolio-navigation-fix.js', sw)
        self.assertNotIn('./market-close-controller.js', sw)
        for name in ('./market.js','./market-runtime-loader.js','./market-live-overlay.js','./market-data-loader.js','./portfolio-sheet-navigation.js','./vestra-ai-brief.js','./portfolio-dossier-routing.js','./dashboard-market-sentiment.js','./dashboard-market-sentiment.css'):
            self.assertIn(name, sw)
        self.assertNotIn('./vestra-portfolio-focus.js', sw)
        self.assertNotIn('./vestra-portfolio-focus.css', sw)

if __name__ == '__main__':
    unittest.main(verbosity=2)
