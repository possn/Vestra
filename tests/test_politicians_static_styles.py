from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


class PoliticiansStaticStyleTests(unittest.TestCase):
    def test_politicians_use_static_stylesheet_but_keep_dynamic_bar_width(self):
        source = read('politicians.js')
        css = read('politicians.css')

        self.assertIn("document.createElement('link')", source)
        self.assertIn("link.rel='stylesheet'", source)
        self.assertIn("politicians.css?v=1.0", source)
        self.assertNotIn("document.createElement('style')", source)
        self.assertNotIn("s.textContent=", source)

        # Trade magnitude is data-driven presentation and must remain dynamic.
        self.assertIn('style="width:${Math.max(7,amountValue(x.amount)/max*100)}%"', source)

        for selector in (
            '.politician-view-tabs',
            '.politician-profile',
            '.politician-bar',
            '.politician-favourite-grid',
            '@media(max-width:620px)',
        ):
            self.assertIn(selector, css)

    def test_service_worker_precaches_politicians_stylesheet(self):
        sw = read('sw.js')
        self.assertIn('./politicians.js', sw)
        self.assertIn('./politicians.css', sw)


if __name__ == '__main__':
    unittest.main(verbosity=2)
