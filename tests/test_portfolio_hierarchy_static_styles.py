from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


class PortfolioHierarchyStaticStyleTests(unittest.TestCase):
    def test_hierarchy_preserves_structure_and_uses_static_stylesheet(self):
        js = read('vestra-portfolio-hierarchy.js')
        css = read('vestra-portfolio-hierarchy.css')
        sw = read('sw.js')

        for group in ("id:'decide'", "id:'optimize'", "id:'monitor'"):
            self.assertIn(group, js)
        self.assertIn('MELHOR MELHORIA DETETADA', js)
        self.assertIn('openScenario()', js)
        self.assertIn('vestra-portfolio-hierarchy.css?v=1.0', js)
        self.assertIn("link.rel='stylesheet'", js)
        self.assertNotIn("document.createElement('style')", js)
        self.assertNotIn('s.textContent=', js)
        self.assertIn('.ux454-nav-title', css)
        self.assertIn('.ux455-swap-summary', css)
        self.assertIn('./vestra-portfolio-hierarchy.css', sw)
        self.assertIn('window.VestraPortfolioHierarchy', js)


if __name__ == '__main__':
    unittest.main(verbosity=2)
