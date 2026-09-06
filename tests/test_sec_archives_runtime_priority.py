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

    def test_explicit_priority_precedes_gap_ranking(self):
        sparse = Metrics("AAA")
        priority = Metrics("ZZZ", present={"roe", "roa", "profit_margin", "operating_margin", "gross_margin", "revenue_growth", "free_cash_flow", "current_ratio", "quick_ratio"})
        ordered = runtime._archive_candidate_order([sparse, priority], priority={"ZZZ"})
        self.assertEqual([row.ticker for row in ordered], ["ZZZ", "AAA"])

    def test_runtime_keeps_pipeline_row_order_after_bounded_archive_pass(self):
        first = Metrics("ZZZ", present={"roe", "roa", "profit_margin", "operating_margin", "gross_margin", "revenue_growth", "free_cash_flow", "current_ratio", "quick_ratio"})
        second = Metrics("AAA")
        rows = [first, second]
        fake_module = FakeSecModule()
        captured = []
        original_archive_enrich = runtime.sec_archives_enrich.enrich
        try:
            def capture(raw, priority=None):
                captured.extend(raw)
                return raw

            runtime.sec_archives_enrich.enrich = capture
            combined = runtime.install(fake_module)
            result = combined(rows)
            self.assertIs(result, rows)
            self.assertEqual([row.ticker for row in result], ["ZZZ", "AAA"])
            self.assertEqual([row.ticker for row in captured], ["AAA", "ZZZ"])
        finally:
            runtime.sec_archives_enrich.enrich = original_archive_enrich


if __name__ == "__main__":
    unittest.main(verbosity=2)
