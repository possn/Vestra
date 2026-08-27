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

    def test_opportunities_use_light_index_natively(self):
        source = read('market-opportunities.js')
        self.assertIn("fetch('./data/stocks-index.json'", source)
        self.assertIn("fetch('./data/stocks.json'", source)
        self.assertLess(source.index("stocks-index.json"), source.index("stocks.json"))
        self.assertIn("window.VestraMarketOpportunities", source)

    def test_canonical_opportunities_own_podium_and_guide(self):
        source = read('market-opportunities.js')
        self.assertIn('function decorate(section)', source)
        self.assertIn('ux454-opportunity-guide', source)
        self.assertIn('ux454-podium-1', source)
        self.assertIn('ux454-rank', source)
        self.assertEqual(source.count('new MutationObserver'), 1)

    def test_portfolio_focus_keeps_existing_state_key_and_css_contract(self):
        source = read('vestra-portfolio-focus.js')
        self.assertIn("vestra-portfolio-focus-v1", source)
        self.assertIn(".ux453-focusbar", source)
        self.assertIn(".ux453-badge", source)
        self.assertIn("data-ux-focus", source)

    def test_service_worker_caches_canonical_modules(self):
        sw = read('sw.js')
        self.assertIn('Vestra Service Worker v9.8', sw)
        self.assertIn('vestra-cache-v112', sw)
        for module in (
            './market-opportunities.js','./vestra-portfolio-focus.js','./vestra-portfolio-hierarchy.js','./vestra-swap-lab.js',
            './market-company-brief.js','./market-metric-cleanup.js','./portfolio-collapsibles.js','./portfolio-card-classifier.js','./portfolio-diagnostics.js',
            './vestra-ai-brief.js','./portfolio-dossier-routing.js',
        ):
            self.assertIn(module, sw)


if __name__ == '__main__':
    unittest.main(verbosity=2)
