"""Regression guard: Low52 lens must not override canonical backend risk classes."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Low52FrontendContractTests(unittest.TestCase):
    def test_low52_observations_are_not_suppressed_by_discovery(self):
        js = (ROOT / "market-opportunities.js").read_text(encoding="utf-8")
        start = js.index("if(lens==='low52'){", js.index("function lensEligible("))
        end = js.index("if(!discoveryEligible(s))return false;", start)
        branch = js[start:end]
        self.assertIn("above<=5", branch)
        self.assertIn("low52_observed_last_session", branch)
        self.assertNotIn("opportunity_eligible", branch)
        self.assertNotIn("coreCandidate", branch)
        self.assertIn("structural_risk:'Risco estrutural'", js)
        self.assertIn("value_trap_risk:'Risco de value trap'", js)
        self.assertIn("Observação de preço, não recomendação", js)

    def test_backend_risk_statuses_remain_non_positive(self):
        source = (ROOT / "scripts/low52_intelligence.py").read_text(encoding="utf-8")
        for status in ("structural_risk", "value_trap_risk", "insufficient"):
            self.assertIn(status, source)


if __name__ == "__main__":
    unittest.main()
