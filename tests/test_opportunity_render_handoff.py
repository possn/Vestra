from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class OpportunityRenderHandoffTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.market = (ROOT / "market.js").read_text(encoding="utf-8")

    def test_discovery_skips_native_shortlist_when_canonical_renderer_is_ready(self):
        start = self.market.index("function renderDiscover()")
        end = self.market.index("\n\n  function low52Stats", start)
        block = self.market[start:end]
        self.assertIn("const canonicalOpportunityRenderer=!qs&&!!window.VestraMarketOpportunities?.refresh;", block)
        self.assertIn("if(!canonicalOpportunityRenderer){", block)
        self.assertIn("canonicalOpportunityRenderer?'':rows.length?", block)

    def test_render_primary_hands_off_immediately_to_canonical_opportunities(self):
        start = self.market.index("function renderPrimary()")
        end = self.market.index("\n\n  const marketSearchSuggestions", start)
        block = self.market[start:end]
        self.assertIn("window.VestraMarketOpportunities?.refresh", block)
        self.assertIn("window.VestraMarketOpportunities.refresh();", block)
        self.assertLess(block.index("root.innerHTML"), block.index("window.VestraMarketOpportunities.refresh();"))

    def test_search_keeps_native_results_path(self):
        start = self.market.index("function renderDiscover()")
        end = self.market.index("\n\n  function low52Stats", start)
        block = self.market[start:end]
        self.assertIn("const canonicalOpportunityRenderer=!qs", block)
        self.assertIn("if(qs) rows=rows.filter", block)


if __name__ == "__main__":
    unittest.main(verbosity=2)
