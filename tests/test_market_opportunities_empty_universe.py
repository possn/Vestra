from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'market-opportunities.js').read_text(encoding='utf-8')


class MarketOpportunitiesEmptyUniverseTests(unittest.TestCase):
    def test_empty_universe_clears_stale_rows_before_returning(self):
        section_lookup = SOURCE.index("const section=[...document.querySelectorAll('.market-section')]")
        list_lookup = SOURCE.index("const list=section.querySelector('.market-list')", section_lookup)
        empty_guard = SOURCE.index("if(!universe.length){", list_lookup)
        clear_rows = SOURCE.index("list.innerHTML='';", empty_guard)
        empty_signature = SOURCE.index("empty-universe:${activeLens}", empty_guard)
        return_empty = SOURCE.index("return [];", empty_guard)
        active_filter = SOURCE.index("const active=section.querySelector('[data-market-sector].is-active')", empty_guard)

        self.assertLess(list_lookup, empty_guard)
        self.assertLess(empty_guard, clear_rows)
        self.assertLess(clear_rows, return_empty)
        self.assertLess(empty_signature, return_empty)
        self.assertLess(return_empty, active_filter)

    def test_empty_universe_no_longer_returns_before_list_cleanup(self):
        self.assertNotIn("if(!section||!universe.length)return [];", SOURCE)
        self.assertIn("if(!section)return [];", SOURCE)
        self.assertIn("if(!universe.length){", SOURCE)


if __name__ == '__main__':
    unittest.main(verbosity=2)
