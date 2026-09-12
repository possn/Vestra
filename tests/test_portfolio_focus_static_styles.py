from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


class PortfolioFocusStaticStyleTests(unittest.TestCase):
    def test_focus_preserves_state_controls_and_uses_static_stylesheet(self):
        js = read('vestra-portfolio-focus.js')
        css = read('vestra-portfolio-focus.css')
        sw = read('sw.js')

        self.assertIn("const FOCUS_KEY='vestra-portfolio-focus-v1'", js)
        self.assertIn('data-ux-focus="focus"', js)
        self.assertIn('data-ux-focus="all"', js)
        self.assertIn('vestra-portfolio-focus.css?v=1.0', js)
        self.assertIn("link.rel='stylesheet'", js)
        self.assertNotIn("document.createElement('style')", js)
        self.assertNotIn('s.textContent=', js)
        self.assertIn('#marketSheetContent[data-ux-focus="focus"]', css)
        self.assertIn('.ux453-badge.is-purple', css)
        self.assertIn('./vestra-portfolio-focus.css', sw)
        self.assertIn('window.VestraPortfolioFocus', js)


if __name__ == '__main__':
    unittest.main(verbosity=2)
