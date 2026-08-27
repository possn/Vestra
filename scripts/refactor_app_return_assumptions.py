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

anchor="""if (![fetchQuote, fetchFxRates, mapWithConcurrency].every(fn => typeof fn === 'function') || !FX_FALLBACK_LOCAL) {\n  throw new Error('VestraMarketClient não foi carregado antes de app.js');\n}\n"""
imports="""\n/* ─── RETURN ASSUMPTIONS — moved to app-return-assumptions.js ─ */\nconst {\n  PASSIVE_DEFAULTS, APPRECIATION_DEFAULTS, DEFAULT_RETURN_SETTINGS,\n  normalizeReturnSettings, getReturnClassDefinitions,\n} = window.VestraReturnAssumptions || {};\nif (!PASSIVE_DEFAULTS || !APPRECIATION_DEFAULTS || !DEFAULT_RETURN_SETTINGS ||\n    typeof normalizeReturnSettings !== 'function' || typeof getReturnClassDefinitions !== 'function') {\n  throw new Error('VestraReturnAssumptions não foi carregado antes de app.js');\n}\n"""
app=once(app,anchor,anchor+imports,'return assumptions import')

pat=r'''const PASSIVE_DEFAULTS = \{.*?\n\};\n\nconst APPRECIATION_DEFAULTS = \{.*?\n\};\n\n(const BROKER_REBUILD_SCHEMA_VERSION = 44;[^\n]*\n)\nconst DEFAULT_RETURN_SETTINGS = \{.*?\n\};\n\nfunction getReturnSettings\(\) \{.*?\n\}\n'''
m=re.search(pat,app,flags=re.S)
if not m: raise SystemExit('return defaults block not found')
broker_line=m.group(1)
replacement=broker_line+"\nfunction getReturnSettings() {\n  return normalizeReturnSettings((state && state.settings && state.settings.returnDefaults) || {}, parseNum);\n}\n"
app=app[:m.start()]+replacement+app[m.end():]

pat=r'''function getReturnClassDefinitions\(\) \{\n  return \[.*?\n  \];\n\}\n\n'''
app,n=re.subn(pat,'',app,count=1,flags=re.S)
if n!=1: raise SystemExit(f'return class definitions extraction: {n}')

for forbidden in ('const PASSIVE_DEFAULTS = {','const APPRECIATION_DEFAULTS = {','const DEFAULT_RETURN_SETTINGS = {'):
    if forbidden in app: raise SystemExit(f'local return default remains: {forbidden}')
write('app.js',app)

index=read('index.html')
index=once(index,
    '<script defer="" src="app-market-client.js?v=1.0"></script>\n<script defer="" fetchpriority="high" src="app.js?v=20260827v12"></script>',
    '<script defer="" src="app-market-client.js?v=1.0"></script>\n<script defer="" src="app-return-assumptions.js?v=1.0"></script>\n<script defer="" fetchpriority="high" src="app.js?v=20260827v13"></script>',
    'index return assumptions')
write('index.html',index)

sw=read('sw.js')
sw=once(sw,'Vestra Service Worker v10.1','Vestra Service Worker v10.2','SW version')
sw=once(sw,'vestra-cache-v115','vestra-cache-v116','SW cache')
sw=once(sw,'  "./app-market-client.js",\n','  "./app-market-client.js",\n  "./app-return-assumptions.js",\n','SW return assumptions')
write('sw.js',sw)

for path in (ROOT/'tests').glob('test_*.py'):
    s=path.read_text(encoding='utf-8')
    s=s.replace('Vestra Service Worker v10.1','Vestra Service Worker v10.2')
    s=s.replace('vestra-cache-v115','vestra-cache-v116')
    path.write_text(s,encoding='utf-8')

(ROOT/'tests/test_app_return_assumptions.py').write_text('''from pathlib import Path\nimport unittest\n\nROOT=Path(__file__).resolve().parents[1]\ndef read(p): return (ROOT/p).read_text(encoding="utf-8")\n\nclass AppReturnAssumptionsTests(unittest.TestCase):\n    def test_defaults_are_preserved_exactly(self):\n        s=read("app-return-assumptions.js")\n        for token in ("'acoes/etfs':1.8", "'depositos':2", "'obrigacoes':3", "'acoes/etfs':6", "'ppr':3.5", "twrMinYears:0.5"):\n            self.assertIn(token,s)\n        self.assertIn("normalizeReturnSettings",s)\n        self.assertIn("getReturnClassDefinitions",s)\n\n    def test_app_uses_shared_assumptions_without_local_duplicates(self):\n        app=read("app.js")\n        self.assertIn("window.VestraReturnAssumptions",app)\n        self.assertIn("normalizeReturnSettings((state && state.settings && state.settings.returnDefaults) || {}, parseNum)",app)\n        self.assertNotIn("const PASSIVE_DEFAULTS = {",app)\n        self.assertNotIn("const APPRECIATION_DEFAULTS = {",app)\n        self.assertNotIn("const DEFAULT_RETURN_SETTINGS = {",app)\n        self.assertNotIn("function getReturnClassDefinitions()",app)\n\n    def test_module_load_order_and_cache(self):\n        index=read("index.html")\n        self.assertLess(index.index('src="app-return-assumptions.js'),index.index('src="app.js'))\n        sw=read("sw.js")\n        self.assertIn("Vestra Service Worker v10.2",sw)\n        self.assertIn("vestra-cache-v116",sw)\n        self.assertIn('./app-return-assumptions.js',sw)\n\nif __name__=='__main__': unittest.main(verbosity=2)\n''',encoding='utf-8')

print('return assumptions extraction prepared')
