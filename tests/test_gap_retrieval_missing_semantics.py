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

    def _row_with_coverage(self, ticker, present_count, quote_type="EQUITY"):
        row = types.SimpleNamespace(ticker=ticker, quote_type=quote_type, error=None)
        for index, key in enumerate(gap_retrieval.CRITICAL):
            setattr(row, key, 1.0 if index < present_count else None)
        return row

    def test_selection_reserves_scanner_capacity_without_raising_total_budget(self):
        # 13/17 = 76.5%: eligible as priority (<85), not as scanner (<68).
        priority_rows = [self._row_with_coverage(f"P{i}", 13) for i in range(100)]
        # 6/17 = 35.3%: clearly sparse global scanner rows.
        scanner_rows = [self._row_with_coverage(f"S{i}", 6) for i in range(100)]
        priority = {row.ticker for row in priority_rows}

        selected, selected_priority, selected_scanner = gap_retrieval._select_candidates(
            priority_rows + scanner_rows,
            priority=priority,
            max_rows=50,
            priority_share=0.60,
        )

        self.assertEqual(len(selected), 50)
        self.assertEqual(selected_priority, 30)
        self.assertEqual(selected_scanner, 20)
        selected_tickers = {row.ticker for _, row in selected}
        self.assertEqual(sum(t in priority for t in selected_tickers), 30)

    def test_selection_reallocates_unused_scanner_capacity_to_priority(self):
        priority_rows = [self._row_with_coverage(f"P{i}", 13) for i in range(100)]
        scanner_rows = [self._row_with_coverage(f"S{i}", 6) for i in range(5)]
        priority = {row.ticker for row in priority_rows}

        selected, selected_priority, selected_scanner = gap_retrieval._select_candidates(
            priority_rows + scanner_rows,
            priority=priority,
            max_rows=50,
            priority_share=0.60,
        )

        self.assertEqual(len(selected), 50)
        self.assertEqual(selected_priority, 45)
        self.assertEqual(selected_scanner, 5)

    def test_high_coverage_priority_does_not_consume_gap_budget(self):
        # 15/17 = 88.2%: above the priority threshold, so a holding with only a
        # small residual gap no longer displaces a materially sparse scanner row.
        rich = self._row_with_coverage("RICH", 15)
        sparse = self._row_with_coverage("SPARSE", 3)
        selected, selected_priority, selected_scanner = gap_retrieval._select_candidates(
            [rich, sparse], priority={"RICH"}, max_rows=1
        )
        self.assertEqual(selected_priority, 0)
        self.assertEqual(selected_scanner, 1)
        self.assertEqual(selected[0][1].ticker, "SPARSE")

    def test_source_contains_no_partial_component_zero_fallbacks(self):
        annual = "".join((SCRIPTS / "gap_retrieval.py").read_text(encoding="utf-8").split())
        quarterly = "".join((SCRIPTS / "quarterly_gap_retrieval.py").read_text(encoding="utf-8").split())
        self.assertNotIn("((cashor0)+(receivablesor0))", annual)
        self.assertNotIn("((cashor0)+(receivablesor0))", quarterly)
        self.assertNotIn("cap+(debtor0)-(cashor0)", annual)
        self.assertNotIn("(current_debtor0)+(long_debtor0)", annual)


if __name__ == "__main__":
    unittest.main(verbosity=2)
