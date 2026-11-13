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

    def test_compact_index_carries_observed_date_and_price_basis(self):
        from scripts.build_market_shards import index_row
        original = {"ticker":"ABC", "low52_observed_last_session":"2026-11-12",
                    "low52_price_basis":"observed_weekly_closes_approximately_52weeks",
                    "low52_observed_close_sessions":52, "low52_above_low_pct":2.4}
        compact = index_row(original)
        for key in ("low52_observed_last_session", "low52_price_basis",
                    "low52_observed_close_sessions", "low52_above_low_pct"):
            self.assertEqual(compact[key], original[key])


if __name__ == "__main__":
    unittest.main()
