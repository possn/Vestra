from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def read(p): return (ROOT/p).read_text(encoding='utf-8')
def write(p,s): (ROOT/p).write_text(s,encoding='utf-8')

def once(s,old,new,label):
    c=s.count(old)
    if c!=1: raise SystemExit(f'{label}: expected 1 occurrence, found {c}')
    return s.replace(old,new,1)

index=read('index.html')
index=once(index,'<script defer="" src="portfolio-navigation-fix.js?v=1.0"></script>','<script defer="" src="portfolio-sheet-navigation.js?v=1.0"></script>','index navigation module')
index=once(index,'<script defer="" src="market-close-controller.js?v=1.0"></script>\n','', 'index close controller')
write('index.html',index)

sw=read('sw.js')
sw=once(sw,'Vestra Service Worker v9.7','Vestra Service Worker v9.8','sw version')
sw=once(sw,'vestra-cache-v111','vestra-cache-v112','sw cache')
sw=once(sw,'  "./portfolio-collapsibles.js",\n','  "./portfolio-collapsibles.js",\n  "./portfolio-sheet-navigation.js",\n','sw navigation module')
sw=once(sw,'  "./market-close-controller.js",\n','', 'sw close controller')
write('sw.js',sw)

# Keep static runtime order aligned with the consolidated module.
p='tests/test_static_market_runtime.py'
s=read(p)
s=s.replace("'portfolio-navigation-fix.js', 'portfolio-card-classifier.js',", "'portfolio-sheet-navigation.js', 'portfolio-card-classifier.js',")
s=s.replace("'market-close-controller.js', 'portfolio-dossier-routing.js',", "'portfolio-dossier-routing.js',")
s=s.replace('Vestra Service Worker v9.7','Vestra Service Worker v9.8').replace('vestra-cache-v111','vestra-cache-v112')
write(p,s)

# Bump generation assertions across architecture tests.
for p in (ROOT/'tests').glob('test_*.py'):
    s=p.read_text(encoding='utf-8')
    ns=s.replace('Vestra Service Worker v9.7','Vestra Service Worker v9.8').replace('vestra-cache-v111','vestra-cache-v112')
    if ns!=s: p.write_text(ns,encoding='utf-8')

# Dedicated invariant for one observer / one close rule.
p=ROOT/'tests/test_portfolio_sheet_navigation.py'
p.write_text('''from pathlib import Path\nimport unittest\n\nROOT=Path(__file__).resolve().parents[1]\n\ndef read(p): return (ROOT/p).read_text(encoding="utf-8")\n\nclass PortfolioSheetNavigationTests(unittest.TestCase):\n    def test_static_runtime_uses_consolidated_navigation(self):\n        index=read("index.html")\n        self.assertIn('portfolio-sheet-navigation.js?v=1.0',index)\n        self.assertNotIn('portfolio-navigation-fix.js',index)\n        self.assertNotIn('market-close-controller.js',index)\n\n    def test_navigation_preserves_close_and_return_contracts(self):\n        s=read("portfolio-sheet-navigation.js")\n        for token in (\n            "sh.dataset.tool='ticker-from-portfolio'",\n            "sh.dataset.returnView='portfolio'",\n            "reopenPortfolioAnalysis()",\n            "closePortfolioToMarket()",\n            "cleanupPortfolioChrome()",\n            "market-close-persistent",\n        ): self.assertIn(token,s)\n        self.assertEqual(s.count('new MutationObserver'),1)\n        self.assertIn('window.VestraPortfolioSheetNavigation',s)\n\n    def test_dossier_routing_remains_separate(self):\n        s=read("portfolio-dossier-routing.js")\n        self.assertIn('tickerFrom',s)\n        self.assertIn('data-market-ticker',s)\n        self.assertNotIn('closePortfolioToMarket',s)\n\n    def test_service_worker_caches_only_consolidated_navigation(self):\n        sw=read("sw.js")\n        self.assertIn('Vestra Service Worker v9.8',sw)\n        self.assertIn('vestra-cache-v112',sw)\n        self.assertIn('./portfolio-sheet-navigation.js',sw)\n        self.assertNotIn('./portfolio-navigation-fix.js',sw)\n        self.assertNotIn('./market-close-controller.js',sw)\n\nif __name__=='__main__': unittest.main(verbosity=2)\n''',encoding='utf-8')

print('portfolio sheet navigation consolidation prepared')
