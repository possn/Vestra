from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class MarketLoaderInvariantTests(unittest.TestCase):
    def test_base_bundle_precedes_market_and_hotfix(self):
        index = read("index.html")
        self.assertLess(index.index('src="app-utils.js'), index.index('src="app.js'))
        self.assertLess(index.index('src="app.js'), index.index('src="market.js'))
        self.assertLess(index.index('src="market.js'), index.index('src="market-hotfix.js'))

    def test_hotfix_does_not_reload_base_utils(self):
        hotfix = read("market-hotfix.js")
        self.assertNotIn("load('./app-utils.js", hotfix)
        self.assertIn("market-data-loader.js", hotfix)

    def test_politicians_loader_matches_canonical_module_version(self):
        hotfix = read("market-hotfix.js")
        politicians = read("politicians.js")
        self.assertIn("const VERSION='2.0';", politicians)
        self.assertIn("politicians.js?v=2.0", hotfix)
        self.assertNotIn("donald-trump", politicians.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
