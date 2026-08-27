from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

def read(path):
    return (ROOT / path).read_text(encoding="utf-8")

class StaticMarketRuntimeTests(unittest.TestCase):
    def test_index_owns_market_module_order_without_dynamic_loader(self):
        index = read("index.html")
        self.assertNotIn('src="market-hotfix.js', index)
        order = [
            'market.js', 'market-data-loader.js', 'market-company-brief.js',
            'market-metric-cleanup.js', 'portfolio-collapsibles.js',
            'portfolio-sheet-navigation.js', 'portfolio-card-classifier.js',
            'market-opportunities.js', 'vestra-portfolio-focus.js',
            'vestra-portfolio-hierarchy.js', 'vestra-swap-lab.js',
            'market-opportunity-lenses.js', 'vestra-ai-brief.js',
            'vestra-portfolio-ui.js', 'portfolio-diagnostics.js',
            'portfolio-dossier-routing.js', 'politicians.js',
        ]
        positions = [index.index(f'src="{name}') for name in order]
        self.assertEqual(positions, sorted(positions))
        for name in order:
            self.assertEqual(index.count(f'src="{name}'), 1, name)
        self.assertNotIn('portfolio-navigation-fix.js', index)
        self.assertNotIn('market-close-controller.js', index)

    def test_every_static_market_script_is_deferred(self):
        index = read("index.html")
        for name in ('market-data-loader.js','portfolio-sheet-navigation.js','market-opportunities.js','vestra-portfolio-ui.js','portfolio-diagnostics.js','politicians.js'):
            self.assertIn(f'<script defer="" src="{name}', index)

    def test_service_worker_tracks_final_static_runtime(self):
        sw = read("sw.js")
        self.assertIn('Vestra Service Worker v10.3', sw)
        self.assertIn('vestra-cache-v117', sw)
        self.assertNotIn('./market-hotfix.js', sw)
        self.assertNotIn('./portfolio-navigation-fix.js', sw)
        self.assertNotIn('./market-close-controller.js', sw)
        for name in ('./market-data-loader.js','./portfolio-sheet-navigation.js','./vestra-ai-brief.js','./portfolio-dossier-routing.js'):
            self.assertIn(name, sw)

if __name__ == '__main__':
    unittest.main(verbosity=2)
