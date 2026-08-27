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


# Portfolio DOM pipeline: collapsibles -> classifier -> hierarchy.
# Keep the responsibilities modular, but let hierarchy own the only child-list
# observer because every hierarchy pass already requires the first two stages.
coll = read('portfolio-collapsibles.js')
coll = replace_once(coll, 'Portfolio Collapsibles v1.0', 'Portfolio Collapsibles v1.1', 'collapsibles header')
coll = replace_once(
    coll,
    "function start(){style();install();let pending=false;const mo=new MutationObserver(()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;install()})});mo.observe(document.body,{childList:true,subtree:true})}",
    "function start(){style();install()}",
    'collapsibles observer',
)
coll = replace_once(coll, "refresh:install,version:'1.0'", "refresh:install,version:'1.1'", 'collapsibles version')
write('portfolio-collapsibles.js', coll)

classifier = read('portfolio-card-classifier.js')
classifier = replace_once(classifier, 'Portfolio Card Classifier v1.0', 'Portfolio Card Classifier v1.1', 'classifier header')
classifier = replace_once(
    classifier,
    "function start(){style();classify();let pending=false;const mo=new MutationObserver(()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;classify();});});mo.observe(document.body,{childList:true,subtree:true});}",
    "function start(){style();classify();}",
    'classifier observer',
)
classifier = replace_once(classifier, "refresh:classify,version:'1.0'", "refresh:classify,version:'1.1'", 'classifier version')
write('portfolio-card-classifier.js', classifier)

hier = read('vestra-portfolio-hierarchy.js')
hier = replace_once(hier, 'Portfolio Hierarchy v1.0', 'Portfolio Hierarchy v1.1', 'hierarchy header')
hier = replace_once(
    hier,
    "  function apply(){\n    const c=root();if(!c)return;\n    decorateBase(c);repairHierarchy(c);fixHeaderCollisions(c);swapLab(c);overlapCard(c);dedupeSurfaces(c);\n  }",
    "  function apply(){\n    window.VestraPortfolioCollapsibles?.refresh?.();\n    window.VestraPortfolioCardClassifier?.refresh?.();\n    const c=root();if(!c)return;\n    decorateBase(c);repairHierarchy(c);fixHeaderCollisions(c);swapLab(c);overlapCard(c);dedupeSurfaces(c);\n  }",
    'hierarchy pipeline',
)
hier = hier.replace("version:'1.0'", "version:'1.1'", 1) if "version:'1.0'" in hier else hier
write('vestra-portfolio-hierarchy.js', hier)

index = read('index.html')
index = replace_once(index, 'portfolio-collapsibles.js?v=1.0', 'portfolio-collapsibles.js?v=1.1', 'index collapsibles version')
index = replace_once(index, 'portfolio-card-classifier.js?v=1.0', 'portfolio-card-classifier.js?v=1.1', 'index classifier version')
index = replace_once(index, 'vestra-portfolio-hierarchy.js?v=1.0', 'vestra-portfolio-hierarchy.js?v=1.1', 'index hierarchy version')
if 'src="market-hotfix.js' in index:
    raise SystemExit('static runtime regressed: market-hotfix.js is active again')
write('index.html', index)

sw = read('sw.js')
sw = replace_once(sw, 'Vestra Service Worker v9.8', 'Vestra Service Worker v9.9', 'SW version')
sw = replace_once(sw, 'vestra-cache-v112', 'vestra-cache-v113', 'SW cache')
write('sw.js', sw)

# Keep all generation/version assertions aligned with the new static generation.
for path in (ROOT / 'tests').glob('test_*.py'):
    source = path.read_text(encoding='utf-8')
    source = source.replace('Vestra Service Worker v9.8', 'Vestra Service Worker v9.9')
    source = source.replace('vestra-cache-v112', 'vestra-cache-v113')
    source = source.replace('portfolio-collapsibles.js?v=1.0', 'portfolio-collapsibles.js?v=1.1')
    source = source.replace('portfolio-card-classifier.js?v=1.0', 'portfolio-card-classifier.js?v=1.1')
    source = source.replace('vestra-portfolio-hierarchy.js?v=1.0', 'vestra-portfolio-hierarchy.js?v=1.1')
    path.write_text(source, encoding='utf-8')

observer_test = ROOT / 'tests/test_portfolio_observer_pipeline.py'
observer_test.write_text('''from pathlib import Path\nimport unittest\n\nROOT=Path(__file__).resolve().parents[1]\n\ndef read(path): return (ROOT/path).read_text(encoding="utf-8")\n\nclass PortfolioObserverPipelineTests(unittest.TestCase):\n    def test_only_hierarchy_observes_the_shared_portfolio_dom_pipeline(self):\n        collapsibles=read("portfolio-collapsibles.js")\n        classifier=read("portfolio-card-classifier.js")\n        hierarchy=read("vestra-portfolio-hierarchy.js")\n        self.assertNotIn("new MutationObserver", collapsibles)\n        self.assertNotIn("new MutationObserver", classifier)\n        self.assertEqual(hierarchy.count("new MutationObserver"),1)\n\n    def test_hierarchy_refreshes_dependencies_in_order_before_layout(self):\n        hierarchy=read("vestra-portfolio-hierarchy.js")\n        a=hierarchy.index("VestraPortfolioCollapsibles?.refresh")\n        b=hierarchy.index("VestraPortfolioCardClassifier?.refresh")\n        c=hierarchy.index("const c=root()", a)\n        self.assertLess(a,b)\n        self.assertLess(b,c)\n\n    def test_static_bundle_keeps_dependency_order_and_cache_busters(self):\n        index=read("index.html")\n        order=["portfolio-collapsibles.js?v=1.1","portfolio-card-classifier.js?v=1.1","vestra-portfolio-hierarchy.js?v=1.1"]\n        positions=[index.index(x) for x in order]\n        self.assertEqual(positions,sorted(positions))\n\nif __name__=='__main__': unittest.main(verbosity=2)\n''', encoding='utf-8')

print('portfolio observer pipeline consolidation prepared')
