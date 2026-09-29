from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class FreshCapitalCanonicalGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.market = (ROOT / "market.js").read_text(encoding="utf-8")

    def test_fresh_capital_consumes_canonical_auto_eligible(self):
        start = self.market.index("function freshCapitalPlan(")
        end = self.market.index("\n  function renderFreshCapitalPlan", start)
        block = self.market[start:end]
        self.assertIn("const baseEligible=decision.autoEligible;", block)
        self.assertNotIn("const baseEligible=strict&&", block)

    def test_canonical_fresh_gate_includes_risk_and_targets(self):
        start = self.market.index("function evaluatePortfolioMove(")
        end = self.market.index("\n  function renderRiskBudget", start)
        block = self.market[start:end]
        self.assertIn("if(mode==='fresh')", block)
        self.assertIn("riskPenalty<5", block)
        self.assertIn("positionPct<=maxPos", block)
        self.assertIn("sectorPct<=maxSector", block)
        self.assertIn("targets.overlap!=='reduce'||indirect<2", block)


if __name__ == "__main__":
    unittest.main(verbosity=2)
