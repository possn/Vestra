from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


class MarketDataHealthStaticStyleTests(unittest.TestCase):
    def test_data_health_preserves_freshness_logic_and_uses_static_stylesheet(self):
        js = read('market-data-health.js')
        css = read('market-data-health.css')
        sw = read('sw.js')

        for token in ('function deriveState', 'function deriveQuoteState', 'function deriveOverallState', 'persistedQuoteSnapshot'):
            self.assertIn(token, js)
        self.assertIn("document.addEventListener('quotesUpdated', refresh)", js)
        self.assertIn('market-data-health.css?v=1.0', js)
        self.assertIn("link.rel = 'stylesheet'", js)
        self.assertNotIn("document.createElement('style')", js)
        self.assertNotIn('style.textContent', js)
        self.assertIn('.vestra-data-health[data-state="ok"]', css)
        self.assertIn('.vestra-data-health__grid', css)
        self.assertIn('./market-data-health.css', sw)
        self.assertIn('window.VestraMarketDataHealth', js)


if __name__ == '__main__':
    unittest.main(verbosity=2)
