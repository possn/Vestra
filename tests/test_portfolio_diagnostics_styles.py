from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


class PortfolioDiagnosticsStyleTests(unittest.TestCase):
    def test_diagnostics_keep_dynamic_state_in_js_and_static_presentation_in_css(self):
        js = read('portfolio-diagnostics.js')
        css = read('portfolio-diagnostics.css')
        self.assertIn("portfolio-diagnostics.css?v=1.0", js)
        self.assertIn("link.rel='stylesheet'", js)
        self.assertNotIn("document.createElement('style')", js)
        self.assertNotIn('s.textContent=', js)
        self.assertIn('bar.style.width=', js)
        self.assertIn("x.style.display='none'", js)
        for token in ('function overlapModel(', 'ETF × ETF', 'AÇÃO + ETF', 'window.VestraPortfolioDiagnostics'):
            self.assertIn(token, js)
        self.assertIn('.vpd-overlap-results{', css)
        self.assertIn('.vpd-overlap-row{', css)

    def test_service_worker_precaches_diagnostics_stylesheet(self):
        sw = read('sw.js')
        self.assertIn('"./portfolio-diagnostics.js"', sw)
        self.assertIn('"./portfolio-diagnostics.css"', sw)


if __name__ == '__main__':
    unittest.main(verbosity=2)
