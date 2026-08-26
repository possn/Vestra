from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


class PortfolioHierarchyArchitectureTests(unittest.TestCase):
    def test_hotfix_uses_canonical_hierarchy(self):
        h=read('market-hotfix.js')
        self.assertIn('compatibility loader v4.95', h)
        self.assertIn("vestra-portfolio-hierarchy.js?v=1.0", h)
        self.assertNotIn('vestra-ux-v455.js', h)
        self.assertNotIn('vestra-ux-v457.js', h)
        self.assertLess(h.index('vestra-portfolio-hierarchy.js'), h.index('vestra-ux-v456.js'))

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

    def test_v454_only_owns_opportunity_presentation_now(self):
        s=read('vestra-ux-v454.js')
        self.assertIn('rankOpportunityRows', s)
        self.assertIn('ux454-podium', s)
        self.assertNotIn('organizePortfolio', s)
        self.assertNotIn('const GROUPS=', s)

    def test_service_worker_caches_hierarchy(self):
        sw=read('sw.js')
        self.assertIn('Vestra Service Worker v9.0', sw)
        self.assertIn('vestra-cache-v104', sw)
        self.assertIn('./vestra-portfolio-hierarchy.js', sw)


if __name__ == '__main__':
    unittest.main(verbosity=2)
