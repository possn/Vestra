from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

def read(path): return (ROOT/path).read_text(encoding="utf-8")

class PortfolioObserverPipelineTests(unittest.TestCase):
    def test_only_hierarchy_observes_the_shared_portfolio_dom_pipeline(self):
        collapsibles=read("portfolio-collapsibles.js")
        classifier=read("portfolio-card-classifier.js")
        hierarchy=read("vestra-portfolio-hierarchy.js")
        self.assertNotIn("new MutationObserver",collapsibles)
        self.assertNotIn("new MutationObserver",classifier)
        self.assertEqual(hierarchy.count("new MutationObserver"),1)

    def test_hierarchy_refreshes_dependencies_in_order_before_layout(self):
        hierarchy=read("vestra-portfolio-hierarchy.js")
        a=hierarchy.index("VestraPortfolioCollapsibles?.refresh")
        b=hierarchy.index("VestraPortfolioCardClassifier?.refresh")
        c=hierarchy.index("const c=root()",a)
        self.assertLess(a,b)
        self.assertLess(b,c)

    def test_static_bundle_uses_fresh_cache_busters(self):
        index=read("index.html")
        order=["portfolio-collapsibles.js?v=1.2","portfolio-card-classifier.js?v=1.2","vestra-portfolio-hierarchy.js?v=1.2"]
        positions=[index.index(x) for x in order]
        self.assertEqual(positions,sorted(positions))
        sw=read("sw.js")
        self.assertIn("Vestra Service Worker v10.10",sw)
        self.assertIn("vestra-cache-v124",sw)

if __name__=='__main__': unittest.main(verbosity=2)
