from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


class CanonicalRuntimeCleanupTests(unittest.TestCase):
    def test_loader_uses_canonical_ai_and_routing_without_versioned_nav_overlays(self):
        h = read('index.html')
        self.assertNotIn('market-hotfix.js', h)
        self.assertIn("vestra-ai-brief.js?v=1.0", h)
        self.assertIn("portfolio-dossier-routing.js?v=1.0", h)
        for legacy in (
            'vestra-ai-brief-v459.js',
            'vestra-portfolio-nav-fix-v464.js',
            'vestra-portfolio-tabs-v479.js',
            'vestra-portfolio-dossier-routing-v482.js',
        ):
            self.assertNotIn(legacy, h)

    def test_ai_brief_preserves_safe_contract_and_index_first_loading(self):
        s = read('vestra-ai-brief.js')
        self.assertIn("fetch('./data/stocks-index.json'", s)
        self.assertIn("fetch('./data/stocks.json'", s)
        self.assertLess(s.index('stocks-index.json'), s.index('stocks.json'))
        self.assertIn("`${base}/ai-brief`", s)
        self.assertIn('não altera Score Vestra nem cria recomendação automática', s)
        self.assertIn('Brief local · sem inventar métricas', s)
        self.assertIn('window.VestraAiBrief', s)

    def test_routing_uses_current_portfolio_controls(self):
        s = read('portfolio-dossier-routing.js')
        for token in ('[data-vpu-toggle]', '[data-vpu-tab]', '[data-vpu-detail]'):
            self.assertIn(token, s)
        for stale in ('[data-ux461-toggle]', '[data-v479-tab]', '[data-v480-tab]'):
            self.assertNotIn(stale, s)
        self.assertIn('window.VestraPortfolioDossierRouting', s)

    def test_no_active_module_dynamically_loads_legacy_tabs(self):
        active = (
            'index.html', 'vestra-portfolio-ui.js', 'portfolio-diagnostics.js',
            'portfolio-card-classifier.js', 'vestra-portfolio-hierarchy.js',
            'portfolio-dossier-routing.js',
        )
        combined = '\n'.join(read(path) for path in active)
        self.assertNotIn('vestra-portfolio-tabs-v479.js', combined)

    def test_service_worker_caches_canonical_modules(self):
        sw = read('sw.js')
        self.assertIn('Vestra Service Worker v10.8', sw)
        self.assertIn('vestra-cache-v122', sw)
        self.assertIn('./vestra-ai-brief.js', sw)
        self.assertIn('./portfolio-dossier-routing.js', sw)
        self.assertNotIn('./market-hotfix.js', sw)
        self.assertNotIn('./vestra-ai-brief-v459.js', sw)
        self.assertNotIn('./vestra-portfolio-nav-fix-v464.js', sw)
        self.assertNotIn('./vestra-portfolio-tabs-v479.js', sw)
        self.assertNotIn('./vestra-portfolio-dossier-routing-v482.js', sw)


if __name__ == '__main__':
    unittest.main(verbosity=2)
