from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MarketDataHealthRefreshOwnershipTests(unittest.TestCase):
    def test_refresh_only_renders_latest_generation(self):
        text = (ROOT / 'market-data-health.js').read_text(encoding='utf-8')
        self.assertIn('let refreshGeneration = 0;', text)
        self.assertIn('const generation = ++refreshGeneration;', text)
        self.assertIn('if (generation === refreshGeneration) render(view, data);', text)

    def test_runtime_race_regression_is_covered(self):
        runtime = (ROOT / 'tests/runtime_market_data_health_refresh_ownership.js').read_text(encoding='utf-8')
        self.assertIn("assert(host.innerHTML.includes('22 atualizadas')", runtime)
        self.assertIn("assert(!host.innerHTML.includes('1 atualizadas')", runtime)


if __name__ == '__main__':
    unittest.main(verbosity=2)
