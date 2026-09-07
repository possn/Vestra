from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PortfolioGlancePolishTests(unittest.TestCase):
    def test_stylesheet_exists_and_keeps_expected_structure(self):
        css = (ROOT / 'portfolio-glance-polish.css').read_text(encoding='utf-8')
        self.assertIn('#viewAssets .portfolio-glance__main', css)
        self.assertIn('grid-template-columns:repeat(3,minmax(0,1fr))', css)
        self.assertIn('#viewAssets .portfolio-glance__stat', css)
        self.assertIn('@media(max-width:560px)', css)

    def test_index_loads_polish_after_base_styles(self):
        html = (ROOT / 'index.html').read_text(encoding='utf-8')
        base = html.index('styles.css')
        polish = html.index('portfolio-glance-polish.css')
        self.assertGreater(polish, base)


if __name__ == '__main__':
    unittest.main(verbosity=2)
