from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def read(p): return (ROOT/p).read_text(encoding='utf-8')
def write(p,s): (ROOT/p).write_text(s,encoding='utf-8')
def once(s,old,new,label):
    n=s.count(old)
    if n!=1: raise SystemExit(f'{label}: expected 1 occurrence, found {n}')
    return s.replace(old,new,1)

app=read('app.js')

# Current corporate/listing identity repairs. These are deliberately narrow.
anchor='''  const YAHOO_TICKER_OVERRIDES = {\n    "WCP": "WCP.TO",'''
replacement='''  const YAHOO_TICKER_OVERRIDES = {\n    // 2026/current identity repairs: avoid venue/crypto collisions.\n    "ENS": "ENS",          // EnerSys, NYSE (not Ethereum Name Service crypto)\n    "MPW": "MPT",          // Medical Properties Trust ticker changed 2026-02-02\n    "MPW.US": "MPT",\n    "EDV": "EDV.TO",       // CAD line; LSE dual-list remains EDV.L when explicit\n    "AMS": "AMS.SW",       // ams-OSRAM Swiss line in CHF\n    "WCP": "WCP.TO",'''
app=once(app,anchor,replacement,'ticker overrides')

# Generic equity ticker resolution must not interpret a stock symbol as crypto.
old='''    // Cripto: BTC, ETH, BTC.CC, "Bitcoin" → BTC-USD (via tabela top 100)\n    const cryptoTk = cryptoToYahoo(t);\n    if (cryptoTk) return cryptoTk;\n    if (t.endsWith(".CC")) return t.replace(/\\.CC$/, "-USD");'''
new='''    // Crypto is resolved earlier from the asset class. Generic equity symbols\n    // must never be reinterpreted as crypto (e.g. ENS = EnerSys, not ENS-USD).\n    if (t.endsWith(".CC")) return t.replace(/\\.CC$/, "-USD");'''
app=once(app,old,new,'generic crypto collision')

# Split-aware historical guard. Keep extreme unexplained jumps rejected.
old='''  const ref = historical > 0 ? historical : baseline;\n  if (ref > 0) {\n    const ratio = priceEur / ref;\n    if (ratio > 5 || ratio < 0.2) {\n      return { ok:false, reason:`Cotação suspeita rejeitada (${ratio.toFixed(1)}× face ao último preço fiável)` };\n    }\n  }'''
new='''  const ref = historical > 0 ? historical : baseline;\n  if (ref > 0) {\n    const ratio = priceEur / ref;\n    if (ratio > 5 || ratio < 0.2) {\n      // Legitimate stock splits can move a sound quote by an exact structural factor.\n      // Only allow common split ratios and only with explicit/high-confidence identity.\n      const splitFactors = [2, 3, 4, 5, 10, 20];\n      const explicitIdentity = !!(asset.isin || asset.yahooTicker || asset.ticker);\n      const splitLike = splitFactors.some(f =>\n        Math.abs(ratio - f) / f <= 0.04 || Math.abs(ratio - (1/f)) / (1/f) <= 0.04\n      );\n      if (!(explicitIdentity && splitLike)) {\n        return { ok:false, reason:`Cotação suspeita rejeitada (${ratio.toFixed(1)}× face ao último preço fiável)` };\n      }\n    }\n  }'''
app=once(app,old,new,'split-aware sanity')

write('app.js',app)

idx=read('index.html')
idx=idx.replace('app.js?v=20260827v16','app.js?v=20260827v17')
write('index.html',idx)

sw=read('sw.js')
sw=sw.replace('Vestra Service Worker v10.5','Vestra Service Worker v10.6')
sw=sw.replace('vestra-cache-v119','vestra-cache-v120')
write('sw.js',sw)

# Keep version invariants current and add focused regression tests.
for path in (ROOT/'tests').glob('test_*.py'):
    s=path.read_text(encoding='utf-8')
    s=s.replace('app.js?v=20260827v16','app.js?v=20260827v17')
    s=s.replace('Vestra Service Worker v10.5','Vestra Service Worker v10.6')
    s=s.replace('vestra-cache-v119','vestra-cache-v120')
    path.write_text(s,encoding='utf-8')

(ROOT/'tests/test_remaining_quote_identity.py').write_text('''from pathlib import Path\nimport unittest\nROOT=Path(__file__).resolve().parents[1]\ndef read(p): return (ROOT/p).read_text(encoding="utf-8")\nclass RemainingQuoteIdentityTests(unittest.TestCase):\n    def test_current_identity_repairs_are_narrow(self):\n        a=read("app.js")\n        for token in ('"ENS": "ENS"','"MPW": "MPT"','"EDV": "EDV.TO"','"AMS": "AMS.SW"'):\n            self.assertIn(token,a)\n        generic=a[a.index('function toYahooTicker'):a.index('function toYahooTicker')+1200]\n        self.assertNotIn('cryptoToYahoo(t)',generic)\n    def test_split_guard_keeps_extremes_blocked(self):\n        a=read("app.js")\n        self.assertIn('const splitFactors = [2, 3, 4, 5, 10, 20]',a)\n        self.assertIn('explicitIdentity && splitLike',a)\n        self.assertIn('Cotação suspeita rejeitada',a)\n    def test_fresh_bundle(self):\n        self.assertIn('app.js?v=20260827v17',read('index.html'))\n        sw=read('sw.js')\n        self.assertIn('Vestra Service Worker v10.6',sw)\n        self.assertIn('vestra-cache-v120',sw)\nif __name__=='__main__': unittest.main(verbosity=2)\n''',encoding='utf-8')
print('remaining quote identity repairs prepared')
