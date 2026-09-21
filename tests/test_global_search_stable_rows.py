from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class GlobalSearchStableRowsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / 'market-global-search.js').read_text(encoding='utf-8')

    def test_async_search_enrichment_reuses_existing_ticker_nodes(self):
        block = self.source.split('function renderGlobalSuggestions(q, rows){', 1)[1].split('async function runSearch(q){', 1)[0]
        self.assertIn("const existing = new Map", block)
        self.assertIn("existing.get(ticker)", block)
        self.assertIn("if (!row) {", block)
        self.assertIn("if (row.innerHTML !== html) row.innerHTML = html;", block)
        self.assertNotIn("box.querySelector('.vestra-global-search')?.remove();", block)

    def test_only_removed_tickers_are_detached(self):
        block = self.source.split('function renderGlobalSuggestions(q, rows){', 1)[1].split('async function runSearch(q){', 1)[0]
        self.assertIn("for (const [ticker,row] of existing) if (!keep.has(ticker)) row.remove();", block)

    def test_broker_alias_survives_when_same_ticker_becomes_local_during_search(self):
        block = self.source.split('function renderGlobalSuggestions(q, rows){', 1)[1].split('async function runSearch(q){', 1)[0]
        self.assertIn("r=>r._brokerAlias || !localExactPresent(r.ticker)", block)


if __name__ == '__main__':
    unittest.main(verbosity=2)
