from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def read(p): return (ROOT/p).read_text(encoding='utf-8')
def write(p,s): (ROOT/p).write_text(s,encoding='utf-8')
def once(s,old,new,label):
    n=s.count(old)
    if n!=1: raise SystemExit(f'{label}: expected 1 occurrence, found {n}')
    return s.replace(old,new,1)

app=read('app.js')

old='''  const assetCcy = String(asset.priceCurrency || asset.currency || "").trim().toUpperCase();\n  const quoteCcy = String(q.currency || "").trim().toUpperCase();\n  const explicit = hasStrongQuoteIdentitySafe(asset);\n  // Currency mismatch is a strong collision signal for explicit broker instruments.\n  if (assetCcy && quoteCcy && assetCcy !== quoteCcy && !(assetCcy === "GBX" && quoteCcy === "GBP")) {\n    if (!String(rawTicker || "").includes("=") && !String(rawTicker || "").endsWith("-USD")) {\n      return { ok:false, reason:`Cotação suspeita: moeda ${quoteCcy} não coincide com ${assetCcy}` };\n    }\n  }\n'''
new='''  const portfolioCcy = String((((state || {}).settings || {}).currency) || "EUR").trim().toUpperCase();\n  const storedPriceCcy = String(asset.priceCurrency || "").trim().toUpperCase();\n  const storedAssetCcy = String(asset.currency || "").trim().toUpperCase();\n  const quoteCcy = String(q.currency || "").trim().toUpperCase();\n  const explicit = hasStrongQuoteIdentitySafe(asset);\n  // Broker imports often store the portfolio-converted value currency (EUR) in\n  // priceCurrency. That is accounting currency, not evidence that GOOGL/TSLA/LSE\n  // instruments themselves trade in EUR. Only a non-base broker price currency is\n  // strong enough to veto Yahoo here; manual assets keep their explicit currency guard.\n  const assetCcy = asset.generatedFromBroker\n    ? ((storedPriceCcy && storedPriceCcy !== portfolioCcy) ? storedPriceCcy : "")\n    : (storedPriceCcy || storedAssetCcy);\n  if (assetCcy && quoteCcy && assetCcy !== quoteCcy && !(assetCcy === "GBX" && quoteCcy === "GBP")) {\n    if (!String(rawTicker || "").includes("=") && !String(rawTicker || "").endsWith("-USD")) {\n      return { ok:false, reason:`Cotação suspeita: moeda ${quoteCcy} não coincide com ${assetCcy}` };\n    }\n  }\n'''
app=once(app,old,new,'quote currency sanity guard')

old='''    if (!sanity.ok) {\n      failed++;\n      errors.push({ raw, yahoo: yahoo || "", assetName: asset.name || raw || "Ativo", reason: sanity.reason });\n      console.warn("[Quote rejected]", asset.name || raw, sanity.reason, q);\n      continue;\n    }\n\n    const priceLabel = ccy === "EUR"\n'''
new='''    if (!sanity.ok) {\n      failed++;\n      errors.push({ raw, yahoo: yahoo || "", assetName: asset.name || raw || "Ativo", reason: sanity.reason });\n      console.warn("[Quote rejected]", asset.name || raw, sanity.reason, q);\n      continue;\n    }\n    // Heal stale broker metadata after ticker identity + sanity checks pass.\n    // Future refreshes then know the instrument's native quote currency instead\n    // of the portfolio accounting currency carried by older imports.\n    if (asset.generatedFromBroker && ccy) asset.priceCurrency = ccy;\n\n    const priceLabel = ccy === "EUR"\n'''
app=once(app,old,new,'heal broker price currency')
write('app.js',app)

index=read('index.html')
index=once(index,'app.js?v=20260827v13','app.js?v=20260827v14','app cachebuster')
write('index.html',index)

sw=read('sw.js')
sw=once(sw,'Vestra Service Worker v10.2','Vestra Service Worker v10.3','SW version')
sw=once(sw,'vestra-cache-v116','vestra-cache-v117','SW cache')
write('sw.js',sw)

for path in (ROOT/'tests').glob('test_*.py'):
    s=path.read_text(encoding='utf-8')
    s=s.replace('Vestra Service Worker v10.2','Vestra Service Worker v10.3')
    s=s.replace('vestra-cache-v116','vestra-cache-v117')
    path.write_text(s,encoding='utf-8')

p=ROOT/'tests/test_quote_currency_guard.py'
p.write_text('''from pathlib import Path\nimport unittest\n\nROOT=Path(__file__).resolve().parents[1]\ndef read(p): return (ROOT/p).read_text(encoding="utf-8")\n\nclass QuoteCurrencyGuardTests(unittest.TestCase):\n    def test_broker_base_currency_is_not_treated_as_native_quote_currency(self):\n        app=read("app.js")\n        self.assertIn("storedPriceCcy !== portfolioCcy",app)\n        self.assertIn("asset.generatedFromBroker",app)\n        self.assertIn("if (asset.generatedFromBroker && ccy) asset.priceCurrency = ccy",app)\n        self.assertIn("Cotação suspeita: moeda ${quoteCcy} não coincide com ${assetCcy}",app)\n\n    def test_manual_assets_keep_explicit_currency_guard(self):\n        app=read("app.js")\n        self.assertIn(": (storedPriceCcy || storedAssetCcy)",app)\n\n    def test_fresh_bundle_is_published(self):\n        index=read("index.html")\n        self.assertIn("app.js?v=20260827v14",index)\n        sw=read("sw.js")\n        self.assertIn("Vestra Service Worker v10.3",sw)\n        self.assertIn("vestra-cache-v117",sw)\n\nif __name__=='__main__': unittest.main(verbosity=2)\n''',encoding='utf-8')

print('broker quote currency guard repair prepared')
