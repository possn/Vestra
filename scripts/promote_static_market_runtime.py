from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


def write(path, text):
    (ROOT / path).write_text(text, encoding='utf-8')


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected exactly 1 occurrence, found {count}')
    return text.replace(old, new, 1)


# Static runtime is already canonical. This follow-up removes the last duplicated
# sheet-navigation pair while preserving the existing defer order.
index = read('index.html')
index = replace_once(
    index,
    '<script defer="" src="portfolio-navigation-fix.js?v=1.0"></script>',
    '<script defer="" src="portfolio-sheet-navigation.js?v=1.0"></script>',
    'index portfolio navigation module',
)
index = replace_once(
    index,
    '<script defer="" src="market-close-controller.js?v=1.0"></script>\n',
    '',
    'index market close controller',
)
if 'src="market-hotfix.js' in index:
    raise SystemExit('static runtime regressed: market-hotfix.js is active again')
write('index.html', index)

sw = read('sw.js')
sw = replace_once(sw, 'Vestra Service Worker v9.7', 'Vestra Service Worker v9.8', 'SW version')
sw = replace_once(sw, 'vestra-cache-v111', 'vestra-cache-v112', 'SW cache')
sw = replace_once(
    sw,
    '  "./portfolio-collapsibles.js",\n',
    '  "./portfolio-collapsibles.js",\n  "./portfolio-sheet-navigation.js",\n',
    'SW portfolio navigation insertion',
)
sw = replace_once(sw, '  "./market-close-controller.js",\n', '', 'SW close controller removal')
if './portfolio-navigation-fix.js' in sw:
    sw = sw.replace('  "./portfolio-navigation-fix.js",\n', '')
write('sw.js', sw)

# Keep generation assertions aligned.
for path in (ROOT / 'tests').glob('test_*.py'):
    source = path.read_text(encoding='utf-8')
    source = source.replace('Vestra Service Worker v9.7', 'Vestra Service Worker v9.8')
    source = source.replace('vestra-cache-v111', 'vestra-cache-v112')
    source = source.replace("'portfolio-navigation-fix.js', 'portfolio-card-classifier.js',", "'portfolio-sheet-navigation.js', 'portfolio-card-classifier.js',")
    source = source.replace("'market-close-controller.js', 'portfolio-dossier-routing.js',", "'portfolio-dossier-routing.js',")
    path.write_text(source, encoding='utf-8')

# Replace static runtime test with the final module order.
static_test = ROOT / 'tests/test_static_market_runtime.py'
static_test.write_text('''from pathlib import Path\nimport unittest\n\nROOT = Path(__file__).resolve().parents[1]\n\ndef read(path):\n    return (ROOT / path).read_text(encoding="utf-8")\n\nclass StaticMarketRuntimeTests(unittest.TestCase):\n    def test_index_owns_market_module_order_without_dynamic_loader(self):\n        index = read("index.html")\n        self.assertNotIn('src="market-hotfix.js', index)\n        order = [\n            'market.js', 'market-data-loader.js', 'market-company-brief.js',\n            'market-metric-cleanup.js', 'portfolio-collapsibles.js',\n            'portfolio-sheet-navigation.js', 'portfolio-card-classifier.js',\n            'market-opportunities.js', 'vestra-portfolio-focus.js',\n            'vestra-portfolio-hierarchy.js', 'vestra-swap-lab.js',\n            'market-opportunity-lenses.js', 'vestra-ai-brief.js',\n            'vestra-portfolio-ui.js', 'portfolio-diagnostics.js',\n            'portfolio-dossier-routing.js', 'politicians.js',\n        ]\n        positions = [index.index(f'src="{name}') for name in order]\n        self.assertEqual(positions, sorted(positions))\n        for name in order:\n            self.assertEqual(index.count(f'src="{name}'), 1, name)\n        self.assertNotIn('portfolio-navigation-fix.js', index)\n        self.assertNotIn('market-close-controller.js', index)\n\n    def test_every_static_market_script_is_deferred(self):\n        index = read("index.html")\n        for name in ('market-data-loader.js','portfolio-sheet-navigation.js','market-opportunities.js','vestra-portfolio-ui.js','portfolio-diagnostics.js','politicians.js'):\n            self.assertIn(f'<script defer="" src="{name}', index)\n\n    def test_service_worker_tracks_final_static_runtime(self):\n        sw = read("sw.js")\n        self.assertIn('Vestra Service Worker v9.8', sw)\n        self.assertIn('vestra-cache-v112', sw)\n        self.assertNotIn('./market-hotfix.js', sw)\n        self.assertNotIn('./portfolio-navigation-fix.js', sw)\n        self.assertNotIn('./market-close-controller.js', sw)\n        for name in ('./market-data-loader.js','./portfolio-sheet-navigation.js','./vestra-ai-brief.js','./portfolio-dossier-routing.js'):\n            self.assertIn(name, sw)\n\nif __name__ == '__main__':\n    unittest.main(verbosity=2)\n''', encoding='utf-8')

# Dedicated invariant: one observer owns sheet return/close behavior.
nav_test = ROOT / 'tests/test_portfolio_sheet_navigation.py'
nav_test.write_text('''from pathlib import Path\nimport unittest\n\nROOT=Path(__file__).resolve().parents[1]\n\ndef read(path): return (ROOT/path).read_text(encoding="utf-8")\n\nclass PortfolioSheetNavigationTests(unittest.TestCase):\n    def test_consolidated_navigation_is_the_only_active_sheet_nav(self):\n        index=read("index.html")\n        self.assertIn('portfolio-sheet-navigation.js?v=1.0',index)\n        self.assertNotIn('portfolio-navigation-fix.js',index)\n        self.assertNotIn('market-close-controller.js',index)\n\n    def test_close_and_return_contracts_are_preserved(self):\n        s=read("portfolio-sheet-navigation.js")\n        for token in (\n            "sh.dataset.tool='ticker-from-portfolio'",\n            "sh.dataset.returnView='portfolio'",\n            'reopenPortfolioAnalysis()',\n            'closePortfolioToMarket()',\n            'cleanupPortfolioChrome()',\n            'market-close-persistent',\n        ): self.assertIn(token,s)\n        self.assertEqual(s.count('new MutationObserver'),1)\n        self.assertIn('window.VestraPortfolioSheetNavigation',s)\n\n    def test_ticker_decoration_stays_separate(self):\n        routing=read("portfolio-dossier-routing.js")\n        self.assertIn('tickerFrom',routing)\n        self.assertIn('data-market-ticker',routing)\n        self.assertNotIn('closePortfolioToMarket',routing)\n\nif __name__=='__main__': unittest.main(verbosity=2)\n''', encoding='utf-8')

print('static runtime + portfolio sheet navigation migration prepared')
