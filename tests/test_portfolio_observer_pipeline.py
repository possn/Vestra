from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

def read(path): return (ROOT/path).read_text(encoding="utf-8")

class PortfolioObserverPipelineTests(unittest.TestCase):
    def test_only_hierarchy_observes_the_shared_portfolio_decorators(self):
        modules = {
            "collapsibles": read("portfolio-collapsibles.js"),
            "classifier": read("portfolio-card-classifier.js"),
            "focus": read("vestra-portfolio-focus.js"),
            "swap": read("vestra-swap-lab.js"),
            "portfolio_ui": read("vestra-portfolio-ui.js"),
            "diagnostics": read("portfolio-diagnostics.js"),
            "dossier_routing": read("portfolio-dossier-routing.js"),
        }
        for name, source in modules.items():
            self.assertNotIn("new MutationObserver", source, name)
        hierarchy=read("vestra-portfolio-hierarchy.js")
        self.assertEqual(hierarchy.count("new MutationObserver"),1)
        self.assertIn("const sh=document.getElementById('marketSheet');if(!sh)return",hierarchy)
        self.assertIn("mo.observe(sh,{childList:true,subtree:true})",hierarchy)
        self.assertNotIn("mo.observe(document.body",hierarchy)

    def test_hierarchy_refreshes_decorators_in_pipeline_order(self):
        hierarchy=read("vestra-portfolio-hierarchy.js")
        collapsibles=hierarchy.index("VestraPortfolioCollapsibles?.refresh")
        classifier=hierarchy.index("VestraPortfolioCardClassifier?.refresh")
        focus=hierarchy.index("VestraPortfolioFocus?.refresh")
        root=hierarchy.index("const c=root()",collapsibles)
        swap=hierarchy.index("VestraSwapLab?.refresh",root)
        ui=hierarchy.index("VestraPortfolioUI?.refresh",swap)
        diagnostics=hierarchy.index("VestraPortfolioDiagnostics?.refresh",ui)
        routing=hierarchy.index("VestraPortfolioDossierRouting?.decorate",diagnostics)
        self.assertLess(collapsibles,classifier)
        self.assertLess(classifier,focus)
        self.assertLess(focus,root)
        self.assertLess(root,swap)
        self.assertLess(swap,ui)
        self.assertLess(ui,diagnostics)
        self.assertLess(diagnostics,routing)

    def test_decorators_keep_explicit_refresh_contracts(self):
        focus=read("vestra-portfolio-focus.js")
        swap=read("vestra-swap-lab.js")
        ui=read("vestra-portfolio-ui.js")
        diagnostics=read("portfolio-diagnostics.js")
        routing=read("portfolio-dossier-routing.js")
        self.assertIn("refresh:portfolioFocus",focus)
        self.assertIn("refresh:apply",swap)
        self.assertIn("window.VestraPortfolioUI=Object.freeze({refresh:apply",ui)
        self.assertIn("window.VestraPortfolioDiagnostics=Object.freeze({refresh:apply",diagnostics)
        self.assertIn("window.VestraPortfolioDossierRouting={version:VERSION,tickerFrom,decorate,openTicker}",routing)
        self.assertIn("version:'1.1'",focus)
        self.assertIn("version:'1.1'",swap)
        self.assertIn("version:'1.2'",ui)
        self.assertIn("version:'1.1'",diagnostics)
        self.assertIn("const VERSION='1.4'",routing)

    def test_childlist_writers_are_idempotent(self):
        hierarchy=read("vestra-portfolio-hierarchy.js")
        ui=read("vestra-portfolio-ui.js")
        diagnostics=read("portfolio-diagnostics.js")
        self.assertIn("panel.dataset.signature",hierarchy)
        self.assertIn("if(button.textContent!=='Ver comparação')",hierarchy)
        self.assertIn("hero.dataset.signature",ui)
        self.assertIn("introTitle.textContent!==meta.title",ui)
        self.assertIn("btn.textContent!==label",ui)
        self.assertIn("host.dataset.signature",diagnostics)
        self.assertIn("function setText(el,value)",diagnostics)

    def test_navigation_observer_remains_separate_and_sheet_scoped(self):
        nav=read("portfolio-sheet-navigation.js")
        self.assertEqual(nav.count("new MutationObserver"),1)
        self.assertIn("const sh=sheet();",nav)
        self.assertIn("mo.observe(sh,{childList:true,subtree:true,attributes:true,attributeFilter:['hidden','class']})",nav)
        self.assertNotIn("mo.observe(document.body",nav)
        self.assertIn("attributeFilter:['hidden','class']",nav)
        self.assertIn("prepareDossierOrigin(origin)",nav)

    def test_static_bundle_keeps_canonical_order(self):
        index=read("index.html")
        runtime_loader=read("market-runtime-loader.js")
        loader=read("market-static-universe.js")
        self.assertNotIn('src="portfolio-collapsibles.js',index)
        self.assertNotIn('src="portfolio-card-classifier.js',index)
        self.assertLess(runtime_loader.index("portfolio-collapsibles.js"), runtime_loader.index("portfolio-card-classifier.js"))
        lazy_order=[
            "vestra-portfolio-focus.js?v=1.1",
            "vestra-swap-lab.js?v=1.1",
            "vestra-portfolio-ui.js?v=1.2",
            "portfolio-diagnostics.js?v=1.1",
            "portfolio-dossier-routing.js?v=1.4",
            "vestra-portfolio-hierarchy.js?v=1.6",
            "vestra-ai-brief.js?v=1.2",
        ]
        positions=[loader.index(x) for x in lazy_order]
        self.assertEqual(positions,sorted(positions))
        for name in (
            'src="vestra-portfolio-focus.js',
            'src="vestra-swap-lab.js',
            'src="vestra-portfolio-ui.js',
            'src="portfolio-diagnostics.js',
            'src="portfolio-dossier-routing.js',
            'src="vestra-portfolio-hierarchy.js',
            'src="vestra-ai-brief.js',
        ):
            self.assertNotIn(name,index)
        sw=read("sw.js")
        self.assertIn('const CACHE_NAME = "vestra-cache-',sw)
        self.assertIn("staleWhileRevalidate",sw)
        for name in ("./vestra-portfolio-focus.js","./vestra-portfolio-hierarchy.js","./vestra-swap-lab.js","./vestra-portfolio-ui.js","./portfolio-diagnostics.js","./portfolio-dossier-routing.js"):
            self.assertIn(name,sw)

if __name__=='__main__': unittest.main(verbosity=2)
