from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PortfolioReinforceGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.market = (ROOT / "market.js").read_text(encoding="utf-8")

    def test_reinforce_gate_is_defined_once_in_evidence(self):
        block = self.market[
            self.market.index("function portfolioMoveEvidence"):
            self.market.index("function evaluatePortfolioMove")
        ]
        self.assertIn("const actionableValuation=['undervalued','fair'].includes(valuation);", block)
        self.assertIn("const strict=conf!=null&&conf>=60&&gate==='clear'&&actionableValuation", block)
        self.assertIn("const reinforceEligible=strict&&conv!=null&&conv>=70;", block)
        self.assertIn("reinforceEligible", block)

    def test_action_and_fresh_capital_share_reinforce_gate(self):
        action = self.market[
            self.market.index("function portfolioAction"):
            self.market.index("const PORTFOLIO_TARGETS_KEY")
        ]
        evaluate = self.market[
            self.market.index("function evaluatePortfolioMove"):
            self.market.index("function renderRiskBudget")
        ]
        self.assertIn("const evidence=portfolioMoveEvidence(stock,conviction);", action)
        self.assertIn("if(evidence.reinforceEligible)", action)
        self.assertIn("const evidence=portfolioMoveEvidence(destination,destinationConv);", evaluate)
        self.assertIn("autoEligible=evidence.reinforceEligible", evaluate)


if __name__ == "__main__":
    unittest.main(verbosity=2)
