from pathlib import Path


def once(text, old, new, label):
    count=text.count(old)
    if count!=1:
        raise SystemExit(f'{label}: expected one match, got {count}')
    return text.replace(old,new,1)

p=Path('worker.js')
s=p.read_text(encoding='utf-8')
s=once(s,' * Versão 4.5 — null-safe fundamentals + fresh quote overlay',' * Versão 4.6 — null-safe quote + fundamentals semantics','version header')
s=once(s,'const cacheKey = `quote41:${ticker.toUpperCase()}`;','const cacheKey = `quote46:${ticker.toUpperCase()}`;','quote cache generation')
s=once(s,'change_pct: Number.isFinite(q.regularMarketChangePercent) ? q.regularMarketChangePercent : 0,','change_pct: Number.isFinite(q.regularMarketChangePercent) ? q.regularMarketChangePercent : null,','v7 change pct')
s=once(s,'div_rate: Number.isFinite(q.trailingAnnualDividendRate) ? q.trailingAnnualDividendRate : 0,','div_rate: Number.isFinite(q.trailingAnnualDividendRate) ? q.trailingAnnualDividendRate : null,','div rate')
s=once(s,'div_yield: Number.isFinite(q.trailingAnnualDividendYield) ? q.trailingAnnualDividendYield : 0,','div_yield: Number.isFinite(q.trailingAnnualDividendYield) ? q.trailingAnnualDividendYield : null,','div yield')
s=once(s,'? ((meta.regularMarketPrice - meta.previousClose) / meta.previousClose) * 100 : 0,','? ((meta.regularMarketPrice - meta.previousClose) / meta.previousClose) * 100 : null,','chart change pct')
s=once(s,'change_pct: Number.isFinite(priceNode?.regularMarketChangePercent?.raw) ? priceNode.regularMarketChangePercent.raw : 0,','change_pct: Number.isFinite(priceNode?.regularMarketChangePercent?.raw) ? priceNode.regularMarketChangePercent.raw : null,','quoteSummary change pct')
s=once(s,'change_pct: 0, sector: "", industry: "", country: "", exchange: "", quote_type: "",','change_pct: null, sector: "", industry: "", country: "", exchange: "", quote_type: "",','html fallback change pct')
s=once(s,'version: "4.5",','version: "4.6",','health version')
s=once(s,'service: "Vestra Market Proxy v4.5",','service: "Vestra Market Proxy v4.6",','root version')
p.write_text(s,encoding='utf-8')

t=Path('tests/test_worker_quote_missing_numeric_semantics.py')
t.write_text('''from pathlib import Path\nimport unittest\n\nROOT=Path(__file__).resolve().parents[1]\n\nclass WorkerQuoteMissingNumericSemanticsTests(unittest.TestCase):\n    @classmethod\n    def setUpClass(cls):\n        cls.worker=(ROOT/'worker.js').read_text(encoding='utf-8')\n\n    def test_quote_cache_generation_is_invalidated(self):\n        self.assertIn('quote46:${ticker.toUpperCase()}', self.worker)\n        self.assertNotIn('quote41:${ticker.toUpperCase()}', self.worker)\n\n    def test_missing_quote_change_is_null_not_zero(self):\n        self.assertIn('q.regularMarketChangePercent : null', self.worker)\n        self.assertIn('priceNode.regularMarketChangePercent.raw : null', self.worker)\n        self.assertIn('change_pct: null, sector:', self.worker)\n        self.assertNotIn('change_pct: 0, sector:', self.worker)\n\n    def test_missing_dividend_fields_are_null_not_zero(self):\n        self.assertIn('q.trailingAnnualDividendRate : null', self.worker)\n        self.assertIn('q.trailingAnnualDividendYield : null', self.worker)\n        self.assertNotIn('q.trailingAnnualDividendRate : 0', self.worker)\n        self.assertNotIn('q.trailingAnnualDividendYield : 0', self.worker)\n\n    def test_worker_version_is_46(self):\n        self.assertIn('Versão 4.6', self.worker)\n        self.assertIn('version: "4.6"', self.worker)\n\nif __name__ == '__main__':\n    unittest.main(verbosity=2)\n''',encoding='utf-8')
