from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


class PortfolioClassifierBadgeStyleTests(unittest.TestCase):
    def test_badges_are_owned_by_classifier_and_focus_assets_are_retired(self):
        js = read('portfolio-card-classifier.js')
        css = read('portfolio-card-classifier.css')
        sw = read('sw.js')

        self.assertIn("portfolio-card-classifier.css?v=1.1", js)
        self.assertIn("link.rel='stylesheet'", js)
        self.assertNotIn("document.createElement('style')", js)
        self.assertNotIn('s.textContent=', js)
        for token in ('TROCAS INTELIGENTES', 'DUPLICAÇÃO DE EXPOSIÇÃO', 'CAPITAL NOVO'):
            self.assertIn(token, js)
        for token in ('.ux-card-badge.is-purple', '.ux-card-badge.is-amber', '.ux-card-badge.is-green'):
            self.assertIn(token, css)
        self.assertIn('./portfolio-card-classifier.css', sw)
        self.assertNotIn('./vestra-portfolio-focus.js', sw)
        self.assertNotIn('./vestra-portfolio-focus.css', sw)
        self.assertIn('window.VestraPortfolioCardClassifier', js)
        self.assertIn("version:'1.6'", js)


if __name__ == '__main__':
    unittest.main(verbosity=2)
