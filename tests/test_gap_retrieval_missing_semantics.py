import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

# These tests exercise pure helpers only; avoid requiring yfinance in the
# lightweight historical suite.
if "yfinance" not in sys.modules:
    yf_stub = types.ModuleType("yfinance")
    yf_stub.Ticker = object
    sys.modules["yfinance"] = yf_stub

import gap_retrieval
import quarterly_gap_retrieval


class GapRetrievalMissingSemanticsTests(unittest.TestCase):
    def test_quarterly_ttm_requires_all_four_quarters(self):
        self.assertEqual(quarterly_gap_retrieval._sum_recent([10.0, 20.0, 30.0, 40.0]), 100.0)
        self.assertIsNone(quarterly_gap_retrieval._sum_recent([10.0, None, 30.0, 40.0]))
        self.assertIsNone(quarterly_gap_retrieval._sum_recent([10.0, 20.0, 30.0]))

    def test_quick_ratio_never_coerces_missing_component_to_zero(self):
        for module in (gap_retrieval, quarterly_gap_retrieval):
            self.assertEqual(module._quick_ratio(20.0, 30.0, 25.0), 2.0)
            self.assertIsNone(module._quick_ratio(None, 30.0, 25.0))
            self.assertIsNone(module._quick_ratio(20.0, None, 25.0))
            self.assertIsNone(module._quick_ratio(20.0, 30.0, None))
            self.assertIsNone(module._quick_ratio(20.0, 30.0, 0.0))

    def test_enterprise_value_requires_debt_and_cash(self):
        self.assertEqual(gap_retrieval._enterprise_value(100.0, 40.0, 10.0), 130.0)
        self.assertIsNone(gap_retrieval._enterprise_value(100.0, None, 10.0))
        self.assertIsNone(gap_retrieval._enterprise_value(100.0, 40.0, None))
        self.assertIsNone(gap_retrieval._enterprise_value(None, 40.0, 10.0))
        self.assertIsNone(gap_retrieval._enterprise_value(10.0, 0.0, 20.0))

    def test_source_contains_no_partial_component_zero_fallbacks(self):
        annual = "".join((SCRIPTS / "gap_retrieval.py").read_text(encoding="utf-8").split())
        quarterly = "".join((SCRIPTS / "quarterly_gap_retrieval.py").read_text(encoding="utf-8").split())
        self.assertNotIn("((cashor0)+(receivablesor0))", annual)
        self.assertNotIn("((cashor0)+(receivablesor0))", quarterly)
        self.assertNotIn("cap+(debtor0)-(cashor0)", annual)
        self.assertNotIn("(current_debtor0)+(long_debtor0)", annual)


if __name__ == "__main__":
    unittest.main(verbosity=2)
