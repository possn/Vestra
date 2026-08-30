from pathlib import Path

p=Path('app.js')
s=p.read_text(encoding='utf-8')
old='''    // Store Yahoo dividend data for projection use (q = quote object in this scope)\n    if (q && q.div_rate !== undefined && q.div_rate > 0) {\n      asset._yahooDiv = {\n        rate: parseNum(q.div_rate) || 0,\n        yield: parseNum(q.div_yield) || 0,\n        exDate: q.ex_div_date || "",\n        payDate: q.div_date || "",\n        currency: (q.currency || "USD"),\n        updatedAt: new Date().toISOString()\n      };\n    }\n'''
new='''    // Yahoo dividend semantics: null means unavailable; explicit 0 means the\n    // source currently reports no trailing dividend. Preserve the last valid\n    // Yahoo observation on null, but clear it on an explicit suspension/zero.\n    if (q && q.div_rate !== undefined && q.div_rate !== null) {\n      if (Number(q.div_rate) > 0) {\n        asset._yahooDiv = {\n          rate: parseNum(q.div_rate) || 0,\n          yield: q.div_yield == null ? null : (parseNum(q.div_yield) || 0),\n          exDate: q.ex_div_date || "",\n          payDate: q.div_date || "",\n          currency: (q.currency || "USD"),\n          updatedAt: new Date().toISOString()\n        };\n      } else if (Number(q.div_rate) === 0) {\n        delete asset._yahooDiv;\n      }\n    }\n'''
if s.count(old)!=1:
    raise SystemExit(f'dividend quote block: expected one match, got {s.count(old)}')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')

t=Path('tests/test_yahoo_dividend_quote_semantics.py')
t.write_text('''from pathlib import Path\nimport unittest\n\nROOT=Path(__file__).resolve().parents[1]\n\nclass YahooDividendQuoteSemanticsTests(unittest.TestCase):\n    @classmethod\n    def setUpClass(cls):\n        cls.app=(ROOT/'app.js').read_text(encoding='utf-8')\n\n    def test_missing_dividend_does_not_clear_last_valid_observation(self):\n        self.assertIn('q.div_rate !== undefined && q.div_rate !== null', self.app)\n\n    def test_explicit_zero_clears_yahoo_dividend_cache(self):\n        self.assertIn('else if (Number(q.div_rate) === 0)', self.app)\n        self.assertIn('delete asset._yahooDiv;', self.app)\n\n    def test_positive_dividend_is_still_persisted(self):\n        self.assertIn('if (Number(q.div_rate) > 0)', self.app)\n        self.assertIn('asset._yahooDiv = {', self.app)\n\n    def test_missing_yield_is_not_coerced_to_zero(self):\n        self.assertIn('yield: q.div_yield == null ? null : (parseNum(q.div_yield) || 0)', self.app)\n\nif __name__ == '__main__':\n    unittest.main(verbosity=2)\n''',encoding='utf-8')
