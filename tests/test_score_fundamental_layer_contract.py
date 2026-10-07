import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ScoreFundamentalLayerContractTests(unittest.TestCase):
    def test_fundamental_score_is_captured_before_risk_gate_caps(self):
        source = (ROOT / "scripts" / "score.py").read_text(encoding="utf-8")
        capture = source.index("fundamental_score = composite")
        risk_gate = source.index('risk_gate = "clear"', capture)
        risk_cap = source.index("composite = min(composite, score_cap)", risk_gate)
        constructor = source.index("score_fundamental=round(fundamental_score", risk_cap)
        self.assertLess(capture, risk_gate)
        self.assertLess(risk_gate, risk_cap)
        self.assertLess(risk_cap, constructor)

    def test_all_scored_ticker_paths_populate_fundamental_score(self):
        score = (ROOT / "scripts" / "score.py").read_text(encoding="utf-8")
        contract = (ROOT / "scripts" / "score_contract.py").read_text(encoding="utf-8")
        self.assertIn("score_fundamental: float | None", score)
        self.assertIn("score_fundamental=round(fundamental_score", score)
        self.assertGreaterEqual(score.count("score_fundamental=None"), 2)
        self.assertIn("score_fundamental=None", contract)


if __name__ == "__main__":
    unittest.main(verbosity=2)
