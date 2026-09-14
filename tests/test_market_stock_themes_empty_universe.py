from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'market-stock-themes-tools.js').read_text(encoding='utf-8')
LOADER = (ROOT / 'market-ui-polish.js').read_text(encoding='utf-8')


class MarketStockThemesEmptyUniverseTests(unittest.TestCase):
    def test_empty_universe_removes_owned_stock_discovery_before_return(self):
        self.assertIn("if (!rows.length) {", SOURCE)
        self.assertIn("root.querySelector('.market-stock-discovery')?.remove();", SOURCE)

    def test_stock_theme_module_and_loader_versions_match(self):
        self.assertIn("version: '1.5'", SOURCE)
        self.assertIn("market-stock-themes-tools.js?v=1.5", LOADER)

    def test_fix_only_targets_stock_theme_owned_surface(self):
        empty_block = SOURCE.split("if (!rows.length) {", 1)[1].split("}", 1)[0]
        self.assertIn(".market-stock-discovery", empty_block)
        self.assertNotIn("root.innerHTML = ''", empty_block)
        self.assertNotIn("root.replaceChildren", empty_block)


if __name__ == '__main__':
    unittest.main(verbosity=2)
