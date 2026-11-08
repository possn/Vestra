"""Regression guard: Low52 lens must not override canonical backend risk classes."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Low52FrontendContractTests(unittest.TestCase):
    def test_frontend_respects_canonical_low52_status(self):
        js = (ROOT / "market-opportunities.js").read_text(encoding="utf-8")
        start = js.index("if(lens==='low52'){", js.index("function lensEligible("))
        end = js.index("if(lens==='emerging')", start)
        branch = js[start:end]
        self.assertIn("s?.low52_status", branch)
        self.assertIn("['opportunity','watch'].includes(canonical)", branch)
        self.assertIn("if(!['opportunity','watch'].includes(canonical))return false", branch)
        self.assertIn("above<=5", branch)

    def test_backend_risk_statuses_remain_non_positive(self):
        source = (ROOT / "scripts/low52_intelligence.py").read_text(encoding="utf-8")
        for status in ("structural_risk", "value_trap_risk", "insufficient"):
            self.assertIn(status, source)


if __name__ == "__main__":
    unittest.main()
