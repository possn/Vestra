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
        self.assertIn("politicians.css?v=1.1", source)
        self.assertNotIn("document.createElement('style')", source)
        self.assertNotIn("s.textContent=", source)

        # Trade magnitude is data-driven presentation and must remain dynamic.
        self.assertIn('style="width:${Math.max(7,amountValue(x.amount)/max*100)}%"', source)

        for selector in (
            '.politician-view-tabs',
            '.politician-profile',
            '.politician-bar',
            '.politician-favourite-grid',
            '.politician-search-field',
            '.politician-search-results',
            '.politician-search-result',
            '@media(max-width:620px)',
        ):
            self.assertIn(selector, css)

    def test_picker_has_live_name_search_and_preserves_full_list(self):
        source = read('politicians.js')
        self.assertIn('data-politician-search', source)
        self.assertIn('data-politician-search-results', source)
        self.assertIn('data-politician-search-result', source)
        self.assertIn('function searchMembers(query)', source)
        self.assertIn('function updateSearchResults(input)', source)
        self.assertIn("document.addEventListener('input'", source)
        self.assertIn("document.addEventListener('keydown'", source)
        self.assertIn('data-politician-select', source)
        self.assertIn("const VERSION='2.2'", source)

    def test_service_worker_precaches_and_refreshes_politicians_runtime(self):
        sw = read('sw.js')
        self.assertIn('./politicians.js', sw)
        self.assertIn('./politicians.css', sw)
        network_first = sw.split('const BOOTSTRAP_NETWORK_FIRST = new Set([', 1)[1].split(']);', 1)[0]
        self.assertIn('"politicians.js"', network_first)


if __name__ == '__main__':
    unittest.main(verbosity=2)
