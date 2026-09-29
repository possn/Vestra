from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PortfolioActionContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.market = (ROOT / "market.js").read_text(encoding="utf-8")

    def test_action_map_uses_canonical_portfolio_fit_flags(self):
        start = self.market.index("function portfolioAction(")
        end = self.market.index("\n  const PORTFOLIO_TARGETS_KEY", start)
        block = self.market[start:end]
        self.assertIn("Array.isArray(ctx.flags)", block)
        self.assertIn("reasons.push(...ctx.flags.slice(0,2))", block)

    def test_action_map_does_not_reintroduce_default_concentration_thresholds(self):
        start = self.market.index("function portfolioAction(")
        end = self.market.index("\n  const PORTFOLIO_TARGETS_KEY", start)
        block = self.market[start:end]
        self.assertNotIn("ctx.positionPct>=10", block)
        self.assertNotIn("ctx.sectorPct>=28", block)
        self.assertNotIn("ctx.indirectPct>=2", block)

    def test_portfolio_fit_remains_the_target_aware_source(self):
        start = self.market.index("function portfolioFit(")
        end = self.market.index("\n  function portfolioFitSummary", start)
        block = self.market[start:end]
        self.assertIn("targets?.maxPosition", block)
        self.assertIn("targets?.maxSector", block)
        self.assertIn("targets?.overlap==='reduce'", block)
        self.assertIn("flags.push", block)


if __name__ == "__main__":
    unittest.main(verbosity=2)
