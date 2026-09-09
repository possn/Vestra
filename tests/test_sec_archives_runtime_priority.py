import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

if "yfinance" not in sys.modules:
    sys.modules["yfinance"] = types.ModuleType("yfinance")

if "requests" not in sys.modules:
    requests_stub = types.ModuleType("requests")
    requests_stub.Session = object
    adapters_stub = types.ModuleType("requests.adapters")
    adapters_stub.HTTPAdapter = object
    sys.modules["requests"] = requests_stub
    sys.modules["requests.adapters"] = adapters_stub

if "urllib3" not in sys.modules:
    urllib3_stub = types.ModuleType("urllib3")
    util_stub = types.ModuleType("urllib3.util")
    retry_stub = types.ModuleType("urllib3.util.retry")

    class Retry:
        def __init__(self, *args, **kwargs):
            pass

    retry_stub.Retry = Retry
    sys.modules["urllib3"] = urllib3_stub
    sys.modules["urllib3.util"] = util_stub
    sys.modules["urllib3.util.retry"] = retry_stub

import sec_archives_runtime as runtime


class Metrics:
    def __init__(self, ticker, present=()):
        self.ticker = ticker
        self.quote_type = "EQUITY"
        fields = (
            "roe", "roa", "profit_margin", "operating_margin", "gross_margin",
            "revenue_growth", "free_cash_flow", "current_ratio", "quick_ratio",
            "debt_to_equity", "interest_expense",
        )
        for field in fields:
            setattr(self, field, 1.0 if field in set(present) else None)


class FakeSecModule:
    def __init__(self):
        self._vestra_sec_archives_installed = False

    def enrich(self, raw, *args, **kwargs):
        return raw


class SecArchivesRuntimePriorityTests(unittest.TestCase):
    def test_nonpriority_rows_are_ranked_by_missing_fundamentals(self):
        mostly_complete = Metrics("ZZZ", present={"roe", "roa", "profit_margin", "operating_margin", "gross_margin", "revenue_growth", "free_cash_flow", "current_ratio", "quick_ratio"})
        sparse = Metrics("AAA", present={"roe"})
        middle = Metrics("MMM", present={"roe", "roa", "profit_margin", "operating_margin", "gross_margin"})
        ordered = runtime._archive_candidate_order([mostly_complete, sparse, middle])
        self.assertEqual([row.ticker for row in ordered], ["AAA", "MMM", "ZZZ"])

    def test_explicit_priority_precedes_gap_ranking_when_it_has_a_real_gap(self):
        sparse = Metrics("AAA")
        priority = Metrics("ZZZ", present={"roe", "roa", "profit_margin", "operating_margin", "gross_margin", "revenue_growth", "free_cash_flow", "current_ratio", "quick_ratio", "debt_to_equity"})
        ordered = runtime._archive_candidate_order([sparse, priority], priority={"ZZZ"})
        self.assertEqual([row.ticker for row in ordered], ["ZZZ", "AAA"])

    def test_one_gap_priority_holding_is_eligible_but_fully_complete_is_not(self):
        one_gap = Metrics(
            "HOLD",
            present={"roe", "roa", "profit_margin", "operating_margin", "gross_margin", "revenue_growth", "free_cash_flow", "current_ratio", "quick_ratio", "debt_to_equity"},
        )
        complete = Metrics(
            "DONE",
            present={"roe", "roa", "profit_margin", "operating_margin", "gross_margin", "revenue_growth", "free_cash_flow", "current_ratio", "quick_ratio", "debt_to_equity", "interest_expense"},
        )
        sparse_scanner = Metrics("SCAN")
        ordered = runtime._archive_candidate_order(
            [complete, one_gap, sparse_scanner], priority={"DONE", "HOLD"}
        )
        self.assertEqual([row.ticker for row in ordered], ["HOLD", "SCAN"])

    def test_balanced_selector_reserves_scanner_capacity(self):
        holdings = [Metrics(f"H{i:03d}") for i in range(20)]
        scanner = [Metrics(f"S{i:03d}") for i in range(20)]
        selected, selected_priority = runtime._balanced_archive_candidates(
            holdings + scanner,
            priority={row.ticker for row in holdings},
            total_budget=10,
            priority_share=0.4,
        )
        self.assertEqual(len(selected), 10)
        self.assertEqual(len(selected_priority), 4)
        self.assertEqual(sum(row.ticker.startswith("S") for row in selected), 6)

    def test_unused_pool_capacity_is_reassigned_without_exceeding_total_budget(self):
        holdings = [Metrics("HOLD")]
        scanner = [Metrics(f"S{i:03d}") for i in range(20)]
        selected, selected_priority = runtime._balanced_archive_candidates(
            holdings + scanner,
            priority={"HOLD"},
            total_budget=10,
            priority_share=0.4,
        )
        self.assertEqual(len(selected), 10)
        self.assertEqual(selected_priority, {"HOLD"})
        self.assertEqual(sum(row.ticker.startswith("S") for row in selected), 9)

    def test_default_total_budget_stays_below_observed_pre_balance_workload(self):
        self.assertEqual(runtime.ARCHIVE_TOTAL_CANDIDATE_BUDGET, 500)
        self.assertLess(runtime.ARCHIVE_TOTAL_CANDIDATE_BUDGET, 511)
        self.assertEqual(runtime.ARCHIVE_MIN_MISSING, 1)

    def test_selector_can_fill_full_budget_with_one_gap_rows(self):
        one_gap_fields = {"roe", "roa", "profit_margin", "operating_margin", "gross_margin", "revenue_growth", "free_cash_flow", "current_ratio", "quick_ratio", "debt_to_equity"}
        holdings = [Metrics(f"H{i:03d}", present=one_gap_fields) for i in range(250)]
        scanner = [Metrics(f"S{i:03d}", present=one_gap_fields) for i in range(400)]
        selected, selected_priority = runtime._balanced_archive_candidates(
            holdings + scanner,
            priority={row.ticker for row in holdings},
            total_budget=500,
            priority_share=0.4,
        )
        self.assertEqual(len(selected), 500)
        self.assertEqual(len(selected_priority), 200)
        self.assertEqual(sum(row.ticker.startswith("S") for row in selected), 300)

    def test_runtime_keeps_pipeline_row_order_after_bounded_archive_pass(self):
        first = Metrics("ZZZ", present={"roe", "roa", "profit_margin", "operating_margin", "gross_margin", "revenue_growth", "free_cash_flow", "current_ratio", "quick_ratio"})
        second = Metrics("AAA")
        rows = [first, second]
        fake_module = FakeSecModule()
        captured = []
        original_budgeted = runtime._budgeted_archive_enrich
        try:
            def capture(raw, priority=None, max_nonpriority=None):
                captured.extend(raw)
                return raw

            runtime._budgeted_archive_enrich = capture
            combined = runtime.install(fake_module)
            result = combined(rows)
            self.assertIs(result, rows)
            self.assertEqual([row.ticker for row in result], ["ZZZ", "AAA"])
            self.assertEqual([row.ticker for row in captured], ["AAA", "ZZZ"])
        finally:
            runtime._budgeted_archive_enrich = original_budgeted


if __name__ == "__main__":
    unittest.main(verbosity=2)