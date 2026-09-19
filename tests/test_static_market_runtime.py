from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

def read(path):
    return (ROOT / path).read_text(encoding="utf-8")

class StaticMarketRuntimeTests(unittest.TestCase):
    def test_index_keeps_only_lazy_market_entrypoints_direct(self):
        index = read("index.html")
        loader = read("market-runtime-loader.js")
        self.assertNotIn('src="market-hotfix.js', index)
        self.assertIn('src="market-runtime-loader.js?v=1.1"', index)
        self.assertIn('src="market-static-universe.js?v=1.13"', index)
        self.assertIn('src="portfolio-sheet-navigation.js?v=1.3"', index)
        for name in (
            'market-live-overlay.js','market.js','market-data-loader.js','market-company-brief.js',
            'market-metric-cleanup.js','portfolio-collapsibles.js','portfolio-card-classifier.js',
            'market-opportunities.js','vestra-portfolio-focus.js','vestra-portfolio-hierarchy.js',
            'vestra-swap-lab.js','market-opportunity-lenses.js','vestra-ai-brief.js',
            'vestra-portfolio-ui.js','portfolio-diagnostics.js','portfolio-dossier-routing.js',
            'politicians.js',
        ):
            self.assertNotIn(f'src="{name}', index)
            self.assertIn(name, loader)
        self.assertNotIn('portfolio-navigation-fix.js', index)
        self.assertNotIn('market-close-controller.js', index)

    def test_lazy_core_preserves_market_dependency_order(self):
        loader = read("market-runtime-loader.js")
        order = [
            'market-live-overlay.js', 'market-congress-live.js', 'market-portfolio-context.js',
            'market-watch-snapshots.js', 'market-dossier-signals.js', 'market-search-suggestions.js',
            'market-row-ui.js', 'market.js', 'market-data-loader.js',
        ]
        positions = [loader.index(name) for name in order]
        self.assertEqual(positions, sorted(positions))
        self.assertIn('setTimeout(() => { void ensureEnhancements(); }, 0);', loader)

    def test_direct_market_entrypoints_are_deferred(self):
        index = read("index.html")
        for name in ('market-runtime-loader.js','market-static-universe.js','portfolio-sheet-navigation.js'):
            self.assertIn(f'<script defer="" src="{name}', index)

    def test_service_worker_tracks_lazy_runtime_and_modules(self):
        sw = read("sw.js")
        self.assertIn('Vestra Service Worker v', sw)
        self.assertRegex(sw, r'vestra-cache-v\d+')
        self.assertIn('staleWhileRevalidate', sw)
        self.assertNotIn('./market-hotfix.js', sw)
        self.assertNotIn('./portfolio-navigation-fix.js', sw)
        self.assertNotIn('./market-close-controller.js', sw)
        for name in (
            './market-runtime-loader.js','./market-live-overlay.js','./market-data-loader.js',
            './portfolio-sheet-navigation.js','./vestra-ai-brief.js','./portfolio-dossier-routing.js'
        ):
            self.assertIn(name, sw)

if __name__ == '__main__':
    unittest.main(verbosity=2)
