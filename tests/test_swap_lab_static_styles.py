from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


class SwapLabStaticStyleTests(unittest.TestCase):
    def test_swap_lab_preserves_comparison_logic_and_uses_static_stylesheet(self):
        js = read('vestra-swap-lab.js')
        css = read('vestra-swap-lab.css')
        sw = read('sw.js')

        for token in ('function priceStats', 'function timing', 'function verdict', 'function comparisonHTML'):
            self.assertIn(token, js)
        self.assertIn('data-market-ticker', js)
        self.assertIn('data-ux456-impact', js)
        self.assertIn('vestra-swap-lab.css?v=1.0', js)
        self.assertIn("link.rel='stylesheet'", js)
        self.assertNotIn("document.createElement('style')", js)
        self.assertNotIn('style.setProperty', js)
        self.assertIn('.ux456-swaplab', css)
        self.assertIn('[data-ux-kind="overlap"]>.market-perspective-head', css)
        self.assertIn('./vestra-swap-lab.css', sw)
        self.assertIn('window.VestraSwapLab', js)


if __name__ == '__main__':
    unittest.main(verbosity=2)
