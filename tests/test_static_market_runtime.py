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
        order = [
            'market-live-overlay.js', 'market-runtime-loader.js', 'market-data-loader.js',
            'market-metric-cleanup.js', 'portfolio-collapsibles.js',
            'portfolio-sheet-navigation.js', 'portfolio-card-classifier.js',
            'vestra-portfolio-focus.js',
            'vestra-portfolio-hierarchy.js', 'vestra-swap-lab.js',
            'vestra-ai-brief.js',
            'vestra-portfolio-ui.js', 'portfolio-diagnostics.js',
            'portfolio-dossier-routing.js',
        ]
        positions = [index.index(f'src="{name}') for name in order]
        self.assertEqual(positions, sorted(positions))
        for name in order:
            self.assertEqual(index.count(f'src="{name}'), 1, name)
        self.assertIn("script.src = 'market.js?v=20260831v2';", loader)
        universe = read("market-static-universe.js")
        for module in (
            "politicians.js?v=2.1",
            "market-opportunities.js?v=1.2",
            "market-opportunity-lenses.js?v=3.0",
            "market-metals.js?v=1.0",
            "market-company-brief.js?v=2.1",
        ):
            self.assertIn(module, universe)
        for direct in (
            'src="politicians.js',
            'src="market-opportunities.js',
            'src="market-opportunity-lenses.js',
            'src="market-metals.js',
            'src="market-company-brief.js',
        ):
            self.assertNotIn(direct, index)
        self.assertNotIn('portfolio-navigation-fix.js', index)
        self.assertNotIn('market-close-controller.js', index)

    def test_every_static_market_script_is_deferred(self):
        index = read("index.html")
        for name in ('market-live-overlay.js','market-runtime-loader.js','market-data-loader.js','portfolio-sheet-navigation.js','vestra-portfolio-ui.js','portfolio-diagnostics.js'):
            self.assertIn(f'<script defer="" src="{name}', index)

    def test_service_worker_tracks_final_static_runtime(self):
        sw = read("sw.js")
        self.assertIn('Vestra Service Worker v', sw)
        self.assertRegex(sw, r'vestra-cache-v\d+')
        self.assertIn('staleWhileRevalidate', sw)
        self.assertNotIn('./market-hotfix.js', sw)
        self.assertNotIn('./portfolio-navigation-fix.js', sw)
        self.assertNotIn('./market-close-controller.js', sw)
        for name in ('./market.js','./market-runtime-loader.js','./market-live-overlay.js','./market-data-loader.js','./portfolio-sheet-navigation.js','./vestra-ai-brief.js','./portfolio-dossier-routing.js'):
            self.assertIn(name, sw)

if __name__ == '__main__':
    unittest.main(verbosity=2)
