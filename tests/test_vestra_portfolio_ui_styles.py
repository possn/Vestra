from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


class VestraPortfolioUiStyleTests(unittest.TestCase):
    def test_portfolio_ui_keeps_dynamic_kpi_widths_and_moves_static_styles_to_css(self):
        js = read('vestra-portfolio-ui.js')
        css = read('vestra-portfolio-ui.css')
        self.assertIn("vestra-portfolio-ui.css?v=1.0", js)
        self.assertIn("link.rel='stylesheet'", js)
        self.assertNotIn("document.createElement('style')", js)
        self.assertNotIn('s.textContent=', js)
        self.assertIn('style="width:${x}%"', js)
        self.assertIn('x.style.display=', js)
        for token in ('const GROUPS =', 'function ensureHero(', 'data-vpu-tab', 'data-vpu-jump', 'vestra.portfolio.analysisTab'):
            self.assertIn(token, js)
        self.assertIn('.vpu-overview{', css)
        self.assertIn('.vpu-tabs-shell{', css)
        self.assertIn('@media(max-width:620px)', css)

    def test_service_worker_precaches_portfolio_ui_stylesheet(self):
        sw = read('sw.js')
        self.assertIn('"./vestra-portfolio-ui.js"', sw)
        self.assertIn('"./vestra-portfolio-ui.css"', sw)


if __name__ == '__main__':
    unittest.main(verbosity=2)
