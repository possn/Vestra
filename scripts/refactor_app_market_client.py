from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]

def read(p): return (ROOT/p).read_text(encoding='utf-8')
def write(p,s): (ROOT/p).write_text(s,encoding='utf-8')
def once(s,old,new,label):
    n=s.count(old)
    if n!=1: raise SystemExit(f'{label}: expected 1 occurrence, found {n}')
    return s.replace(old,new,1)

app=read('app.js')

anchor="""if (![estimateEURFactorFromRow, parseBrokerLedgerRows, parseBrokerPositionRows,\n      parseXTBTradesRows, parseXTBPositionsRows, parseXTBCashRows,\n      parseBrokerImportFile, parseTrading212HoldingsPdf].every(fn => typeof fn === 'function')) {\n  throw new Error('VestraBrokerParsers não foi carregado antes de app.js');\n}\n"""
market_import="""\n/* ─── MARKET CLIENT — moved to app-market-client.js ───────── */\nconst { fetchQuote, fetchFxRates, mapWithConcurrency, FX_FALLBACK_LOCAL } = window.VestraMarketClient || {};\nif (![fetchQuote, fetchFxRates, mapWithConcurrency].every(fn => typeof fn === 'function') || !FX_FALLBACK_LOCAL) {\n  throw new Error('VestraMarketClient não foi carregado antes de app.js');\n}\n"""
app=once(app,anchor,anchor+market_import,'market client import anchor')

pat=r"\nasync function fetchQuote\(ticker, workerUrl\) \{.*?\n\}\n\n\nfunction hasStrongQuoteIdentitySafe"
app,n=re.subn(pat,"\nfunction hasStrongQuoteIdentitySafe",app,count=1,flags=re.S)
if n!=1: raise SystemExit(f'fetchQuote extraction: {n}')

pat=r"\nasync function mapWithConcurrency\(items, concurrency, fn\) \{.*?\n\}\n\n  const rawTickerRefs"
app,n=re.subn(pat,"\n  const rawTickerRefs",app,count=1,flags=re.S)
if n!=1: raise SystemExit(f'mapWithConcurrency extraction: {n}')

old="""  const fxRates = {};\n  const FX_FALLBACK_LOCAL = {USD:0.92,GBP:1.17,DKK:0.134,CHF:1.05,PLN:0.23,\n    SEK:0.087,NOK:0.085,CAD:0.68,AUD:0.59,JPY:0.006,HKD:0.118};\n  await Promise.allSettled([...ccysNeeded].map(async ccy => {\n    try {\n      const fq = await fetchQuote(`EUR${ccy}=X`, workerUrl);\n      if (fq && fq.price > 0) fxRates[ccy] = 1 / fq.price;\n    } catch(_) {}\n  }));\n  for (const c of ccysNeeded) if (!fxRates[c]) fxRates[c] = FX_FALLBACK_LOCAL[c] || 1;\n"""
new="""  const fxRates = await fetchFxRates(ccysNeeded, workerUrl, FX_FALLBACK_LOCAL);\n"""
app=once(app,old,new,'global FX client')

old="""          const FX_LOCAL = {USD:0.92, GBP:1.17, CHF:1.05, CAD:0.68, AUD:0.59,\n            DKK:0.134, SEK:0.087, NOK:0.085, PLN:0.23, JPY:0.006};\n          fxToEur = FX_LOCAL[ccy] || 1;\n"""
app=once(app,old,"          fxToEur = FX_FALLBACK_LOCAL[ccy] || 1;\n",'manual FX fallback')

if app.count('async function fetchQuote(')!=0: raise SystemExit('local fetchQuote remains')
if app.count('async function mapWithConcurrency(')!=0: raise SystemExit('local mapWithConcurrency remains')
write('app.js',app)

index=read('index.html')
index=once(index,'<script defer="" src="app-broker-parsers.js?v=1.0"></script>\n<script defer="" fetchpriority="high" src="app.js?v=20260824v11"></script>',
           '<script defer="" src="app-broker-parsers.js?v=1.0"></script>\n<script defer="" src="app-market-client.js?v=1.0"></script>\n<script defer="" fetchpriority="high" src="app.js?v=20260827v12"></script>',
           'index app market client')
write('index.html',index)

sw=read('sw.js')
sw=once(sw,'Vestra Service Worker v10.0','Vestra Service Worker v10.1','SW version')
sw=once(sw,'vestra-cache-v114','vestra-cache-v115','SW cache')
sw=once(sw,'  "./app-broker-parsers.js",\n','  "./app-broker-parsers.js",\n  "./app-market-client.js",\n','SW market client shell')
write('sw.js',sw)

for path in (ROOT/'tests').glob('test_*.py'):
    s=path.read_text(encoding='utf-8')
    s=s.replace('Vestra Service Worker v10.0','Vestra Service Worker v10.1')
    s=s.replace('vestra-cache-v114','vestra-cache-v115')
    path.write_text(s,encoding='utf-8')

test=ROOT/'tests/test_app_market_client.py'
test.write_text('''from pathlib import Path\nimport unittest\n\nROOT=Path(__file__).resolve().parents[1]\ndef read(p): return (ROOT/p).read_text(encoding="utf-8")\n\nclass AppMarketClientTests(unittest.TestCase):\n    def test_client_owns_transport_fx_and_concurrency(self):\n        s=read("app-market-client.js")\n        for token in ("async function fetchQuote", "async function fetchFxRates", "async function mapWithConcurrency", "FX_FALLBACK_LOCAL", "AbortSignal.timeout(10000)"):\n            self.assertIn(token,s)\n        self.assertIn("window.VestraMarketClient",s)\n\n    def test_app_imports_client_without_duplicate_implementations(self):\n        app=read("app.js")\n        self.assertIn("window.VestraMarketClient",app)\n        self.assertNotIn("async function fetchQuote(ticker, workerUrl)",app)\n        self.assertNotIn("async function mapWithConcurrency(items, concurrency, fn)",app)\n        self.assertIn("fetchFxRates(ccysNeeded, workerUrl, FX_FALLBACK_LOCAL)",app)\n        self.assertIn("FX_FALLBACK_LOCAL[ccy] || 1",app)\n\n    def test_client_loads_before_app_and_is_cached(self):\n        index=read("index.html")\n        self.assertLess(index.index('src="app-market-client.js'),index.index('src="app.js'))\n        self.assertIn('app-market-client.js?v=1.0',index)\n        sw=read("sw.js")\n        self.assertIn("Vestra Service Worker v10.1",sw)\n        self.assertIn("vestra-cache-v115",sw)\n        self.assertIn('./app-market-client.js',sw)\n\nif __name__=='__main__': unittest.main(verbosity=2)\n''',encoding='utf-8')

print('app market client extraction prepared')
