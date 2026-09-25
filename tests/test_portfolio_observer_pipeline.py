from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

def read(path): return (ROOT/path).read_text(encoding="utf-8")

class PortfolioObserverPipelineTests(unittest.TestCase):
    def test_only_hierarchy_observes_the_shared_portfolio_decorators(self):
        modules = {
            "collapsibles": read("portfolio-collapsibles.js"),
            "classifier": read("portfolio-card-classifier.js"),
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
        self.assertIn("const observerOptions={childList:true,subtree:true}",hierarchy)
        self.assertIn("mo.disconnect()",hierarchy)
        self.assertIn("mo.takeRecords()",hierarchy)
        self.assertIn("mo.observe(sh,observerOptions)",hierarchy)
        self.assertIn("try{apply();}finally{",hierarchy)
        self.assertNotIn("mo.observe(document.body",hierarchy)

    def test_hierarchy_refreshes_decorators_in_pipeline_order(self):
        hierarchy=read("vestra-portfolio-hierarchy.js")
        collapsibles=hierarchy.index("VestraPortfolioCollapsibles?.refresh")
        classifier=hierarchy.index("VestraPortfolioCardClassifier?.refresh")
        root=hierarchy.index("const c=root()",collapsibles)
        swap=hierarchy.index("VestraSwapLab?.refresh",root)
        ui=hierarchy.index("VestraPortfolioUI?.refresh",swap)
        diagnostics=hierarchy.index("VestraPortfolioDiagnostics?.refresh",ui)
        routing=hierarchy.index("VestraPortfolioDossierRouting?.decorate",diagnostics)
        self.assertLess(collapsibles,classifier)
        self.assertLess(classifier,root)
        self.assertNotIn("VestraPortfolioFocus",hierarchy)
        self.assertLess(root,swap)
        self.assertLess(swap,ui)
        self.assertLess(ui,diagnostics)
        self.assertLess(diagnostics,routing)

    def test_decorators_keep_explicit_refresh_contracts(self):
        swap=read("vestra-swap-lab.js")
        ui=read("vestra-portfolio-ui.js")
        diagnostics=read("portfolio-diagnostics.js")
        routing=read("portfolio-dossier-routing.js")
        self.assertIn("refresh:apply",swap)
        self.assertIn("window.VestraPortfolioUI=Object.freeze({refresh:apply",ui)
        self.assertIn("window.VestraPortfolioDiagnostics=Object.freeze({refresh:apply",diagnostics)
        self.assertIn("window.VestraPortfolioDossierRouting={version:VERSION,tickerFrom,decorate,openTicker}",routing)
        self.assertIn("version:'1.2'",swap)
        self.assertIn("version:'2.6'",ui)
        self.assertIn("version:'1.2'",diagnostics)
        self.assertIn("const VERSION='1.5'",routing)

    def test_observer_ignores_presentation_only_mutations(self):
        hierarchy=read("vestra-portfolio-hierarchy.js")
        self.assertIn("function relevantMutation(m)",hierarchy)
        self.assertIn("mutations.some(relevantMutation)",hierarchy)
        self.assertIn("presentationOnly=node=>",hierarchy)
        self.assertIn(".vpu-overview,.vpu-reveal,.vpu-tabs-shell,.ux456-swaplab",hierarchy)
        self.assertIn("return !nodes.every(presentationOnly)",hierarchy)

    def test_companions_defer_initial_refresh_to_hierarchy_bootstrap(self):
        swap=read("vestra-swap-lab.js")
        ui=read("vestra-portfolio-ui.js")
        diagnostics=read("portfolio-diagnostics.js")
        routing=read("portfolio-dossier-routing.js")
        self.assertIn("function start(){addStyle();}",swap)
        self.assertIn("function start(){style();try{",ui)
        self.assertNotIn("catch{} apply();}",ui)
        self.assertIn("function start(){style();}",diagnostics)
        self.assertIn("function start(){}",routing)
        hierarchy=read("vestra-portfolio-hierarchy.js")
        for token in (
            "VestraSwapLab?.refresh?.()",
            "VestraPortfolioUI?.refresh?.()",
            "VestraPortfolioDiagnostics?.refresh?.()",
            "VestraPortfolioDossierRouting?.decorate?.()",
        ):
            self.assertIn(token,hierarchy)

    def test_diagnosis_toggle_has_single_owner(self):
        ui=read("vestra-portfolio-ui.js")
        diagnostics=read("portfolio-diagnostics.js")
        self.assertNotIn("const d=e.target.closest?.('[data-vpu-detail]')",ui)
        self.assertIn("const btn=e.target.closest?.('[data-vpu-detail]')",diagnostics)

    def test_exploration_keeps_one_decision_card_open(self):
        ui = (ROOT / "vestra-portfolio-ui.js").read_text(encoding="utf-8")
        self.assertIn("function focusCard(c,target)", ui)
        self.assertIn("function collapseActive(c)", ui)
        self.assertIn("focusCard(c,target)", ui)
        self.assertIn("el.classList.contains('vpu-hidden')||el===target", ui)

    def test_optimize_is_a_connected_three_step_journey(self):
        ui = (ROOT / "vestra-portfolio-ui.js").read_text(encoding="utf-8")
        css = (ROOT / "vestra-portfolio-ui.css").read_text(encoding="utf-8")
        self.assertIn("function syncOptimizeGuide(c,target=null)", ui)
        self.assertIn("aria-current", ui)
        self.assertIn("vpu-step-state", ui)
        self.assertIn("button.is-current", css)
        self.assertIn("button:not(:last-child)::after", css)

    def test_priority_and_monitor_paths_expose_scan_cues(self):
        ui = (ROOT / "vestra-portfolio-ui.js").read_text(encoding="utf-8")
        css = (ROOT / "vestra-portfolio-ui.css").read_text(encoding="utf-8")
        self.assertIn("function syncGroupScan(c,tabs)", ui)
        self.assertIn("vpu-tab-count", ui)
        self.assertIn("vpu-card-cue", ui)
        self.assertIn("Research pendente", ui)
        self.assertIn("Stress test", ui)
        self.assertIn(".vpu-tab-count", css)
        self.assertIn(".vpu-card-cue", css)

    def test_exploration_avoids_repeated_header_copy(self):
        ui = (ROOT / "vestra-portfolio-ui.js").read_text(encoding="utf-8")
        self.assertIn("<strong>Escolhe o foco</strong>", ui)
        self.assertEqual(ui.count("<small>EXPLORAR A CARTEIRA</small>"), 1)
        self.assertIn("active==='optimize'?'Segue os três passos abaixo.':''", ui)

    def test_exploration_is_scan_first_until_explicit_card_intent(self):
        ui = (ROOT / "vestra-portfolio-ui.js").read_text(encoding="utf-8")
        self.assertIn("function collapseActive(c)", ui)
        self.assertNotIn("function openFirstActive(c)", ui)
        self.assertIn("if(opening){collapseActive(c);", ui)
        self.assertIn("apply();const c=root();if(c){collapseActive(c);", ui)
        self.assertIn("focusCard(c,target)", ui)

    def test_foundation_helpers_defer_dom_work_to_hierarchy_bootstrap(self):
        collapsibles=read("portfolio-collapsibles.js")
        classifier=read("portfolio-card-classifier.js")
        hierarchy=read("vestra-portfolio-hierarchy.js")
        self.assertIn("function start(){style()}",collapsibles)
        self.assertIn("function start(){style();}",classifier)
        self.assertNotIn("function start(){style();install()}",collapsibles)
        self.assertNotIn("function start(){style();classify();}",classifier)
        self.assertIn("VestraPortfolioCollapsibles?.refresh?.()",hierarchy)
        self.assertIn("VestraPortfolioCardClassifier?.refresh?.()",hierarchy)

    def test_collapsibles_do_not_build_hidden_global_toolbar(self):
        collapsibles=read("portfolio-collapsibles.js")
        css=read("portfolio-collapsibles.css")
        hierarchy=read("vestra-portfolio-hierarchy.js")
        self.assertNotIn("data-collapse-all",collapsibles)
        self.assertNotIn("market-collapse-toolbar",collapsibles)
        self.assertNotIn(".market-collapse-toolbar{",css)
        self.assertIn("c.querySelector('.market-decision-center')",hierarchy)
        self.assertIn("version:'1.6'",collapsibles)
        self.assertIn("function toggleCard(card)",collapsibles)
        self.assertIn("card.tabIndex=0",collapsibles)
        self.assertIn("aria-expanded",collapsibles)
        self.assertIn(".is-collapsed{cursor:pointer}",css)
        self.assertIn(":not(.vpu-card-cue)",css)
        self.assertIn("portfolio-collapsibles.css?v=1.2",collapsibles)

    def test_classifier_does_not_build_hidden_legacy_shortcuts(self):
        classifier=read("portfolio-card-classifier.js")
        css=read("portfolio-card-classifier.css")
        self.assertNotIn("ux-portfolio-shortcuts",classifier)
        self.assertNotIn("data-ux-jump",classifier)
        self.assertNotIn("jumpPortfolio",classifier)
        self.assertNotIn("ux-portfolio-shortcuts",css)
        self.assertIn("version:'1.5'",classifier)

    def test_classifier_owns_portfolio_badges(self):
        classifier=read("portfolio-card-classifier.js")
        css=read("portfolio-card-classifier.css")
        for token in ("TROCAS INTELIGENTES","DUPLICAÇÃO DE EXPOSIÇÃO","CAPITAL NOVO"):
            self.assertIn(token,classifier)
        for token in (".ux-card-badge.is-purple",".ux-card-badge.is-amber",".ux-card-badge.is-green"):
            self.assertIn(token,css)
        self.assertNotIn("ux453-badge",classifier)
        self.assertNotIn("ux453-badge",css)

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
            "vestra-swap-lab.js?v=1.2",
            "vestra-portfolio-ui.js?v=2.6",
            "portfolio-diagnostics.js?v=1.2",
            "portfolio-dossier-routing.js?v=1.5",
            "vestra-portfolio-hierarchy.js?v=2.1",
            "vestra-ai-brief.js?v=1.2",
        ]
        positions=[loader.index(x) for x in lazy_order]
        self.assertEqual(positions,sorted(positions))
        for name in (
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
        for name in ("./vestra-portfolio-hierarchy.js","./vestra-swap-lab.js","./vestra-portfolio-ui.js","./portfolio-diagnostics.js","./portfolio-dossier-routing.js"):
            self.assertIn(name,sw)
        self.assertNotIn("./vestra-portfolio-focus.js",sw)
        self.assertNotIn("./vestra-portfolio-focus.css",sw)
        self.assertNotIn("vestra-portfolio-focus.js",loader)

if __name__=='__main__': unittest.main(verbosity=2)
