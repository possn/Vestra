from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class WorkerQuoteMissingNumericSemanticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.worker=(ROOT/'worker.js').read_text(encoding='utf-8')

    def test_quote_cache_generation_is_invalidated(self):
        self.assertIn('quote46:${ticker.toUpperCase()}', self.worker)
        self.assertNotIn('quote41:${ticker.toUpperCase()}', self.worker)

    def test_missing_quote_change_is_null_not_zero(self):
        self.assertIn('q.regularMarketChangePercent : null', self.worker)
        self.assertIn('priceNode.regularMarketChangePercent.raw : null', self.worker)
        self.assertIn('change_pct: null, sector:', self.worker)
        self.assertNotIn('change_pct: 0, sector:', self.worker)

    def test_missing_dividend_fields_are_null_not_zero(self):
        self.assertIn('q.trailingAnnualDividendRate : null', self.worker)
        self.assertIn('q.trailingAnnualDividendYield : null', self.worker)
        self.assertNotIn('q.trailingAnnualDividendRate : 0', self.worker)
        self.assertNotIn('q.trailingAnnualDividendYield : 0', self.worker)

    def test_worker_version_is_46(self):
        self.assertIn('Versão 4.6', self.worker)
        self.assertIn('version: "4.6"', self.worker)

if __name__ == '__main__':
    unittest.main(verbosity=2)
