from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


class PortfolioHierarchyArchitectureTests(unittest.TestCase):
    def test_hotfix_uses_canonical_hierarchy_and_swap_lab(self):
        h=read('index.html')
        self.assertNotIn('market-hotfix.js', h)
        self.assertIn("portfolio-card-classifier.js?v=1.2", h)
        self.assertIn("vestra-portfolio-hierarchy.js?v=1.2", h)
        self.assertIn("vestra-swap-lab.js?v=1.0", h)
        self.assertIn("portfolio-diagnostics.js?v=1.0", h)
        self.assertIn("vestra-ai-brief.js?v=1.0", h)
        self.assertIn("portfolio-dossier-routing.js?v=1.0", h)
        for legacy in ('vestra-ux-v452.js','vestra-ux-v454.js','vestra-ux-v455.js','vestra-ux-v456.js','vestra-ux-v457.js','market-enhancements.js','vestra-portfolio-nav-fix-v464.js','vestra-portfolio-tabs-v479.js','vestra-portfolio-dossier-routing-v482.js'):
            self.assertNotIn(legacy, h)
        self.assertLess(h.index('portfolio-collapsibles.js'), h.index('portfolio-card-classifier.js'))
        self.assertLess(h.index('portfolio-card-classifier.js'), h.index('vestra-portfolio-hierarchy.js'))
        self.assertLess(h.index('vestra-portfolio-hierarchy.js'), h.index('vestra-swap-lab.js'))
        self.assertLess(h.index('vestra-portfolio-ui.js'), h.index('portfolio-diagnostics.js'))
        self.assertLess(h.index('portfolio-diagnostics.js'), h.index('portfolio-dossier-routing.js'))

    def test_hierarchy_preserves_final_card_order_and_swap_hooks(self):
        s=read('vestra-portfolio-hierarchy.js')
        for token in (
            "['research','priority','reinforce','review']",
            "['swap','scenario','overlap','map']",
            "['target','history','risk','stress']",
            'ux454-swap-head','ux454-overlap-head','ux455-swap-summary','ux455-overlap-note',
        ):
            self.assertIn(token, s)
        self.assertEqual(s.count('new MutationObserver'), 1)

    def test_swap_lab_preserves_v456_contract(self):
        s=read('vestra-swap-lab.js')
        for token in (
            "cmp('qualidade',n(a?.score),n(b?.score),true,3)",
            "cmp('timing',timing(a),timing(b),true,5)",
            "cmp('confiança',n(a?.confidence_score),n(b?.confidence_score),true,5)",
            "cmp('ROE',n(a?.roe),n(b?.roe),true,0.02)",
            "cmp('FCF yield',n(a?.free_cash_flow_yield_pct),n(b?.free_cash_flow_yield_pct),true,1)",
            "cmp('Forward P/E',n(a?.forward_pe),n(b?.forward_pe),false,2)",
            'ux456-swaplab','data-ux456-impact','window.VestraSwapLab',
        ):
            self.assertIn(token, s)
        self.assertEqual(s.count('new MutationObserver'), 1)

    def test_service_worker_caches_hierarchy_and_swap_lab(self):
        sw=read('sw.js')
        self.assertIn('Vestra Service Worker v10.3', sw)
        self.assertIn('vestra-cache-v117', sw)
        self.assertIn('./portfolio-card-classifier.js', sw)
        self.assertIn('./vestra-portfolio-hierarchy.js', sw)
        self.assertIn('./vestra-swap-lab.js', sw)
        self.assertIn('./portfolio-collapsibles.js', sw)
        self.assertIn('./portfolio-diagnostics.js', sw)
        self.assertIn('./vestra-ai-brief.js', sw)
        self.assertIn('./portfolio-dossier-routing.js', sw)


if __name__ == '__main__':
    unittest.main(verbosity=2)
