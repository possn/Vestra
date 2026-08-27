from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def read(p): return (ROOT/p).read_text(encoding='utf-8')
def write(p,s): (ROOT/p).write_text(s,encoding='utf-8')
def once(s,old,new,label):
    n=s.count(old)
    if n!=1: raise SystemExit(f'{label}: expected 1 occurrence, found {n}')
    return s.replace(old,new,1)

app=read('app.js')
anchor="""if (![fetchQuote, fetchFxRates, mapWithConcurrency].every(fn => typeof fn === 'function') || !FX_FALLBACK_LOCAL) {
  throw new Error('VestraMarketClient não foi carregado antes de app.js');
}
"""
imp="""
/* ─── QUOTE ERROR DIAGNOSTICS — moved to app-quote-errors.js ─ */
const { summarizeQuoteErrors, decorateQuoteError } = window.VestraQuoteErrors || {};
if (![summarizeQuoteErrors, decorateQuoteError].every(fn => typeof fn === 'function')) {
  throw new Error('VestraQuoteErrors não foi carregado antes de app.js');
}
"""
app=once(app,anchor,anchor+imp,'quote diagnostics import')

count=app.count('return errors.map(err => {')
if count!=2: raise SystemExit(f'error render maps: expected 2, found {count}')
app=app.replace('return errors.map(err => {','return errors.map(err => {\n    err = decorateQuoteError(err);')

old='<div><b>Motivo:</b> ${escapeHtml(reason || "Erro desconhecido")}</div>'
new='<div><b>Categoria:</b> ${escapeHtml((isObj && err.categoryLabel) || "Outro")}</div>\n          <div><b>Motivo:</b> ${escapeHtml(reason || "Erro desconhecido")}</div>'
count=app.count(old)
if count!=2: raise SystemExit(f'category render targets: expected 2, found {count}')
app=app.replace(old,new)

old='summary.textContent = `${updatedCount} actualizado${updatedCount !== 1 ? "s" : ""} com sucesso · ${failedCount} falha${failedCount !== 1 ? "s" : ""}`;'
new='''const groups = summarizeQuoteErrors(errors || []);
  const groupText = groups.length ? ` · ${groups.map(g => `${g.label}: ${g.count}`).join(" · ")}` : "";
  summary.textContent = `${updatedCount} actualizado${updatedCount !== 1 ? "s" : ""} com sucesso · ${failedCount} falha${failedCount !== 1 ? "s" : ""}${groupText}`;'''
app=once(app,old,new,'modal grouped summary')
write('app.js',app)

index=read('index.html')
index=once(index,'<script defer="" src="app-market-client.js?v=1.0"></script>\n','<script defer="" src="app-market-client.js?v=1.0"></script>\n<script defer="" src="app-quote-errors.js?v=1.0"></script>\n','index quote diagnostics')
index=index.replace('app.js?v=20260827v14','app.js?v=20260827v15')
write('index.html',index)

sw=read('sw.js')
sw=sw.replace('Vestra Service Worker v10.3','Vestra Service Worker v10.4')
sw=sw.replace('vestra-cache-v117','vestra-cache-v118')
sw=once(sw,'  "./app-market-client.js",\n','  "./app-market-client.js",\n  "./app-quote-errors.js",\n','SW quote diagnostics')
write('sw.js',sw)

for path in (ROOT/'tests').glob('test_*.py'):
    s=path.read_text(encoding='utf-8').replace('Vestra Service Worker v10.3','Vestra Service Worker v10.4').replace('vestra-cache-v117','vestra-cache-v118')
    path.write_text(s,encoding='utf-8')

(ROOT/'tests/test_quote_error_classifier.py').write_text('''from pathlib import Path\nimport unittest\nROOT=Path(__file__).resolve().parents[1]\ndef read(p): return (ROOT/p).read_text(encoding="utf-8")\nclass QuoteErrorClassifierTests(unittest.TestCase):\n    def test_classifier_has_actionable_buckets(self):\n        s=read("app-quote-errors.js")\n        for token in ("Sem dados Yahoo","Ticker / identidade","Delisted / ignorado","Rede / Worker","Sanity de preço","summarizeQuoteErrors"):\n            self.assertIn(token,s)\n    def test_app_uses_classifier_only_for_diagnostics(self):\n        app=read("app.js")\n        self.assertIn("window.VestraQuoteErrors",app)\n        self.assertIn("Categoria:</b>",app)\n        self.assertIn("summarizeQuoteErrors(errors || [])",app)\n        self.assertNotIn("classifyQuoteError(asset",app)\n    def test_module_load_order_and_cache(self):\n        idx=read("index.html")\n        self.assertLess(idx.index('src="app-quote-errors.js'),idx.index('src="app.js'))\n        sw=read("sw.js")\n        self.assertIn("Vestra Service Worker v10.4",sw)\n        self.assertIn("vestra-cache-v118",sw)\n        self.assertIn('./app-quote-errors.js',sw)\nif __name__=='__main__': unittest.main(verbosity=2)\n''',encoding='utf-8')
print('quote error classifier integration prepared')
