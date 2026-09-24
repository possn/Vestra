from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


class PortfolioFocusStaticStyleTests(unittest.TestCase):
    def test_focus_is_badges_only_and_uses_static_stylesheet(self):
        js = read('vestra-portfolio-focus.js')
        css = read('vestra-portfolio-focus.css')
        sw = read('sw.js')

        self.assertNotIn("FOCUS_KEY", js)
        self.assertNotIn('data-ux-focus', js)
        self.assertNotIn('localStorage', js)
        self.assertIn('vestra-portfolio-focus.css?v=1.1', js)
        self.assertIn("link.rel='stylesheet'", js)
        self.assertNotIn("document.createElement('style')", js)
        self.assertNotIn('s.textContent=', js)
        self.assertNotIn('#marketSheetContent[data-ux-focus="focus"]', css)
        self.assertNotIn('.ux453-focusbar', css)
        self.assertIn('.ux453-badge.is-purple', css)
        self.assertIn('.ux453-badge.is-amber', css)
        self.assertIn('.ux453-badge.is-green', css)
        self.assertIn('./vestra-portfolio-focus.css', sw)
        self.assertIn('window.VestraPortfolioFocus', js)
        self.assertIn("version:'1.2'", js)


if __name__ == '__main__':
    unittest.main(verbosity=2)
