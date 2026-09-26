import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("opportunity_rank", ROOT / "scripts" / "opportunity_rank.py")
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


def row(confidence=70, risk_gate="clear"):
    prices = [100 + i * 0.15 for i in range(90)]
    return {
        "ticker": "TEST",
        "quote_type": "EQUITY",
        "score": 72,
        "confidence_score": confidence,
        "data_coverage_pct": 82,
        "critical_metric_coverage_pct": 80,
        "score_reliability": "robust",
        "risk_gate": risk_gate,
        "price_history_1y": [{"close": p} for p in prices],
        "moat_score": 68,
        "capital_allocation_intelligence_score": 65,
        "qarp_score": 71,
        "value_trap_risk_score": 25,
        "sector_native_score": 67,
        "low52_opportunity_score": 60,
        "recovery_score": 64,
        "valuation_score": 62,
        "estimate_signal": "improving",
        "recovery_status": "recovering",
        "thesis_direction": "up",
    }


class DiscoveryScoreContractTests(unittest.TestCase):
    def test_higher_confidence_does_not_buy_ranking_points_after_gate(self):
        low = MOD.assess(row(confidence=60))
        high = MOD.assess(row(confidence=95))
        self.assertTrue(low["opportunity_eligible"])
        self.assertTrue(high["opportunity_eligible"])
        self.assertEqual(low["opportunity_score_raw"], high["opportunity_score_raw"])

    def test_confidence_still_gates_insufficient_evidence(self):
        out = MOD.assess(row(confidence=49))
        self.assertFalse(out["opportunity_eligible"])
        self.assertIsNone(out["opportunity_score"])
        self.assertIn("Confiança", out["opportunity_suppressed_reason"])

    def test_risk_gate_constrains_discovery_instead_of_rewarding_it(self):
        clear = MOD.assess(row(risk_gate="clear"))
        severe = MOD.assess(row(risk_gate="severe"))
        self.assertEqual(clear["opportunity_score_raw"], severe["opportunity_score_raw"])
        self.assertLessEqual(severe["opportunity_score"], 35)
        self.assertTrue(any(cap["reason"] == "Risk Gate severe" for cap in severe["opportunity_caps"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
