from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class YahooDividendQuoteSemanticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=(ROOT/'app.js').read_text(encoding='utf-8')

    def test_missing_dividend_does_not_clear_last_valid_observation(self):
        self.assertIn('q.div_rate !== undefined && q.div_rate !== null', self.app)

    def test_explicit_zero_clears_yahoo_dividend_cache(self):
        self.assertIn('else if (Number(q.div_rate) === 0)', self.app)
        self.assertIn('delete asset._yahooDiv;', self.app)

    def test_positive_dividend_is_still_persisted(self):
        self.assertIn('if (Number(q.div_rate) > 0)', self.app)
        self.assertIn('asset._yahooDiv = {', self.app)

    def test_missing_yield_is_not_coerced_to_zero(self):
        self.assertIn('yield: q.div_yield == null ? null : (parseNum(q.div_yield) || 0)', self.app)

if __name__ == '__main__':
    unittest.main(verbosity=2)
