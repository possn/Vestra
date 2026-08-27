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


static_block = '''<script defer="" src="market-data-loader.js?v=2.0"></script>
<script defer="" src="market-company-brief.js?v=1.0"></script>
<script defer="" src="market-metric-cleanup.js?v=1.0"></script>
<script defer="" src="portfolio-collapsibles.js?v=1.0"></script>
<script defer="" src="portfolio-navigation-fix.js?v=1.0"></script>
<script defer="" src="portfolio-card-classifier.js?v=1.0"></script>
<script defer="" src="market-opportunities.js?v=1.1"></script>
<script defer="" src="vestra-portfolio-focus.js?v=1.0"></script>
<script defer="" src="vestra-portfolio-hierarchy.js?v=1.0"></script>
<script defer="" src="vestra-swap-lab.js?v=1.0"></script>
<script defer="" src="market-opportunity-lenses.js?v=1.0"></script>
<script defer="" src="vestra-ai-brief.js?v=1.0"></script>
<script defer="" src="vestra-portfolio-ui.js?v=1.0"></script>
<script defer="" src="portfolio-diagnostics.js?v=1.0"></script>
<script defer="" src="market-close-controller.js?v=1.0"></script>
<script defer="" src="portfolio-dossier-routing.js?v=1.0"></script>
<script defer="" src="politicians.js?v=2.1"></script>'''

index = read('index.html')
index = replace_once(
    index,
    '<script defer="" src="market-hotfix.js?v=20260826v1"></script>',
    static_block,
    'index market-hotfix entry',
)
write('index.html', index)

sw = read('sw.js')
sw = replace_once(sw, 'Vestra Service Worker v9.6', 'Vestra Service Worker v9.7', 'SW version')
sw = replace_once(sw, 'vestra-cache-v110', 'vestra-cache-v111', 'SW cache')
sw = replace_once(sw, '  "./market-hotfix.js",\n', '', 'SW hotfix shell entry')
write('sw.js', sw)

# Update architecture tests from dynamic compatibility loader to static defer bundle.
path = 'tests/test_market_loader_invariants.py'
s = read(path)
s = s.replace('def test_base_bundle_precedes_market_and_hotfix(self):', 'def test_base_bundle_precedes_static_market_modules(self):')
s = s.replace("        self.assertLess(index.index('src=\"market.js'), index.index('src=\"market-hotfix.js'))\n", "        self.assertLess(index.index('src=\"market.js'), index.index('src=\"market-data-loader.js'))\n        self.assertLess(index.index('src=\"market-data-loader.js'), index.index('src=\"politicians.js'))\n        self.assertNotIn('src=\"market-hotfix.js', index)\n")
s = s.replace('    def test_hotfix_does_not_reload_base_utils(self):\n        hotfix = read("market-hotfix.js")\n        self.assertNotIn("load(\'./app-utils.js", hotfix)\n        self.assertIn("market-data-loader.js?v=2.0", hotfix)\n', '    def test_static_market_bundle_does_not_reload_base_utils(self):\n        index = read("index.html")\n        self.assertEqual(index.count(\'src="app-utils.js\'), 1)\n        self.assertIn(\'market-data-loader.js?v=2.0\', index)\n')
s = s.replace('        hotfix = read("market-hotfix.js")\n        politicians = read("politicians.js")', '        index = read("index.html")\n        politicians = read("politicians.js")')
s = s.replace('        self.assertIn("politicians.js?v=2.1", hotfix)', '        self.assertIn("politicians.js?v=2.1", index)')
write(path, s)

for path in ('tests/test_market_enhancement_split.py','tests/test_market_opportunities_architecture.py','tests/test_portfolio_hierarchy_architecture.py'):
    s = read(path)
    s = s.replace("h = read('market-hotfix.js')", "h = read('index.html')")
    s = s.replace("h=read('market-hotfix.js')", "h=read('index.html')")
    s = s.replace("hotfix = read('market-hotfix.js')", "hotfix = read('index.html')")
    s = s.replace("self.assertIn('compatibility loader v5.01', h)\n", "self.assertNotIn('market-hotfix.js', h)\n")
    s = s.replace("self.assertIn('compatibility loader v5.01', hotfix)\n", "self.assertNotIn('market-hotfix.js', hotfix)\n")
    s = s.replace('Vestra Service Worker v9.6', 'Vestra Service Worker v9.7')
    s = s.replace('vestra-cache-v110', 'vestra-cache-v111')
    write(path, s)

path = 'tests/test_canonical_runtime_cleanup.py'
s = read(path)
s = s.replace("h = read('market-hotfix.js')", "h = read('index.html')")
s = s.replace("self.assertIn('compatibility loader v5.01', h)\n", "self.assertNotIn('market-hotfix.js', h)\n")
s = s.replace("            'market-hotfix.js', 'vestra-portfolio-ui.js', 'portfolio-diagnostics.js',", "            'index.html', 'vestra-portfolio-ui.js', 'portfolio-diagnostics.js',")
s = s.replace('Vestra Service Worker v9.6', 'Vestra Service Worker v9.7')
s = s.replace('vestra-cache-v110', 'vestra-cache-v111')
s = s.replace("        self.assertIn('./portfolio-dossier-routing.js', sw)\n", "        self.assertIn('./portfolio-dossier-routing.js', sw)\n        self.assertNotIn('./market-hotfix.js', sw)\n")
write(path, s)

path = 'tests/test_portfolio_diagnostics.py'
s = read(path)
s = s.replace("h = read('market-hotfix.js')", "h = read('index.html')")
write(path, s)

path = 'tests/test_native_market_loading.py'
s = read(path)
s = s.replace('Vestra Service Worker v9.6', 'Vestra Service Worker v9.7')
s = s.replace('vestra-cache-v110', 'vestra-cache-v111')
write(path, s)

# Dedicated static-loading invariant.
static_test = ROOT / 'tests/test_static_market_runtime.py'
static_test.write_text('''from pathlib import Path\nimport unittest\n\nROOT = Path(__file__).resolve().parents[1]\n\ndef read(path):\n    return (ROOT / path).read_text(encoding="utf-8")\n\nclass StaticMarketRuntimeTests(unittest.TestCase):\n    def test_index_owns_market_module_order_without_dynamic_loader(self):\n        index = read("index.html")\n        self.assertNotIn('src="market-hotfix.js', index)\n        order = [\n            'market.js', 'market-data-loader.js', 'market-company-brief.js',\n            'market-metric-cleanup.js', 'portfolio-collapsibles.js',\n            'portfolio-navigation-fix.js', 'portfolio-card-classifier.js',\n            'market-opportunities.js', 'vestra-portfolio-focus.js',\n            'vestra-portfolio-hierarchy.js', 'vestra-swap-lab.js',\n            'market-opportunity-lenses.js', 'vestra-ai-brief.js',\n            'vestra-portfolio-ui.js', 'portfolio-diagnostics.js',\n            'market-close-controller.js', 'portfolio-dossier-routing.js',\n            'politicians.js',\n        ]\n        positions = [index.index(f'src="{name}') for name in order]\n        self.assertEqual(positions, sorted(positions))\n        for name in order:\n            self.assertEqual(index.count(f'src="{name}'), 1, name)\n\n    def test_every_static_market_script_is_deferred(self):\n        index = read("index.html")\n        for name in ('market-data-loader.js','market-opportunities.js','vestra-portfolio-ui.js','portfolio-diagnostics.js','politicians.js'):\n            self.assertIn(f'<script defer="" src="{name}', index)\n\n    def test_service_worker_no_longer_caches_compatibility_loader(self):\n        sw = read("sw.js")\n        self.assertIn('Vestra Service Worker v9.7', sw)\n        self.assertIn('vestra-cache-v111', sw)\n        self.assertNotIn('./market-hotfix.js', sw)\n        for name in ('./market-data-loader.js','./vestra-ai-brief.js','./portfolio-dossier-routing.js'):\n            self.assertIn(name, sw)\n\nif __name__ == '__main__':\n    unittest.main(verbosity=2)\n''', encoding='utf-8')

print('static market runtime migration prepared')
