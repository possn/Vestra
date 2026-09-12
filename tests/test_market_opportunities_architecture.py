from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


class CanonicalMarketOpportunityTests(unittest.TestCase):
    def test_hotfix_loads_canonical_modules_not_legacy_opportunity_overlays(self):
        hotfix = read('index.html')
        self.assertIn("market-opportunities.js?v=1.1", hotfix)
        self.assertIn("vestra-portfolio-focus.js?v=1.0", hotfix)
        self.assertNotIn("vestra-ux-v452.js", hotfix)
        self.assertNotIn("vestra-ux-v453.js", hotfix)
        self.assertNotIn("vestra-ux-v454.js", hotfix)
        self.assertLess(hotfix.index('market-opportunities.js'), hotfix.index('market-opportunity-lenses.js'))

    def test_canonical_opportunity_engine_keeps_v453_contract(self):
        source = read('market-opportunities.js')
        for token in (
            "sc==null||sc<58||cov==null||cov<55||conf==null||conf<50",
            "return timing(s)>=48 && confirmed(s)>=2",
            "[n(s?.score),.23]",
            "[timing(s),.27]",
            "[n(s?.recovery_score),.10]",
            "[n(s?.qarp_score),.10]",
            "[n(s?.moat_score),.07]",
            "[n(s?.capital_allocation_intelligence_score),.05]",
            "[n(s?.confidence_score),.06]",
            "[n(s?.value_pct),.06]",
            "[n(s?.growth_pct),.03]",
            "[n(s?.sector_native_score),.03]",
            "Math.min(5,confirmed(s)*1.25)",
        ):
            self.assertIn(token, source)

    def test_opportunities_reuse_canonical_market_universe_without_refetch(self):
        source = read('market-opportunities.js')
        universe = read('market-static-universe.js')
        self.assertIn("window.VestraMarketStaticUniverse", source)
        self.assertIn("getStocks", source)
        self.assertNotIn("fetch('./data/stocks-index.json'", source)
        self.assertNotIn("fetch('./data/stocks.json'", source)
        self.assertIn("function getStocks()", universe)
        self.assertIn("sharedStocks = stocks", universe)
        self.assertIn("window.VestraMarketOpportunities", source)

    def test_strategy_lenses_rank_from_full_universe_not_current_twelve_rows(self):
        source = read('market-opportunities.js')
        lenses = read('market-opportunity-lenses.js')
        self.assertIn("universe.filter(s=>lensEligible(s,activeLens))", source)
        self.assertIn("rows.sort((a,b)=>lensScore(b,activeLens)-lensScore(a,activeLens)", source)
        self.assertIn("function lensEligible(s,lens)", source)
        self.assertIn("function lensScore(s,lens)", source)
        self.assertIn("above>=-0.5&&above<=5", source)
        self.assertIn("!['confirmed','recovering'].includes(rec)", source)
        self.assertIn("window.VestraMarketOpportunities?.selectLens?.(activeLens)", lenses)
        self.assertNotIn("function lensMatch(row, lens)", lenses)
        self.assertNotIn("querySelectorAll('.market-list .market-row')", lenses)

    def test_empty_lens_clears_previous_rows_instead_of_leaving_stale_candidates(self):
        source = read('market-opportunities.js')
        self.assertNotIn("if(!rows.length)return", source)
        self.assertIn("list.innerHTML=rows.map(s=>row(s,activeLens)).join('')", source)
        self.assertIn("||'empty'", source)

    def test_canonical_opportunities_own_podium_guide_and_static_styles(self):
        source = read('market-opportunities.js')
        css = read('market-opportunities.css')
        self.assertIn('function decorate(section)', source)
        self.assertIn('ux454-opportunity-guide', source)
        self.assertIn('ux454-podium-1', source)
        self.assertIn('ux454-rank', source)
        self.assertIn('data-market-ticker', source)
        self.assertEqual(source.count('new MutationObserver'), 1)
        self.assertIn("market-opportunities.css?v=1.0", source)
        self.assertIn("link.rel='stylesheet'", source)
        self.assertNotIn("document.createElement('style')", source)
        self.assertNotIn('s.textContent=', source)
        for selector in ('.ux453-opp{', '.ux454-opportunity-guide{', '.ux454-podium-1{', '.ux454-rank{'):
            self.assertIn(selector, css)

    def test_portfolio_focus_keeps_existing_state_key_and_css_contract(self):
        source = read('vestra-portfolio-focus.js')
        self.assertIn("vestra-portfolio-focus-v1", source)
        self.assertIn(".ux453-focusbar", source)
        self.assertIn(".ux453-badge", source)
        self.assertIn("data-ux-focus", source)

    def test_service_worker_caches_canonical_modules(self):
        sw = read('sw.js')
        self.assertIn('const CACHE_NAME = "vestra-cache-', sw)
        self.assertIn('staleWhileRevalidate', sw)
        for module in (
            './market-live-overlay.js','./market-opportunities.js','./market-opportunities.css','./vestra-portfolio-focus.js','./vestra-portfolio-hierarchy.js','./vestra-swap-lab.js',
            './market-company-brief.js','./market-metric-cleanup.js','./portfolio-collapsibles.js','./portfolio-card-classifier.js','./portfolio-diagnostics.js',
            './vestra-ai-brief.js','./portfolio-dossier-routing.js','./market-opportunity-lenses.js','./mobile-ui-refresh.js',
        ):
            self.assertIn(module, sw)


if __name__ == '__main__':
    unittest.main(verbosity=2)
