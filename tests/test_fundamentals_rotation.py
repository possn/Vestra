import ast
import datetime
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
# Rotation budget is deterministic; this file intentionally avoids network access.
RUN_PATH = ROOT / "scripts" / "run.py"


def load_selector():
    source = RUN_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_select_nonpriority_refresh")
    module = ast.Module(body=[fn], type_ignores=[])
    ns = {"datetime": datetime}
    exec(compile(ast.fix_missing_locations(module), str(RUN_PATH), "exec"), ns)
    return ns["_select_nonpriority_refresh"]


class FundamentalsRotationTests(unittest.TestCase):
    def test_missing_snapshots_are_refreshed_before_cached_rotation(self):
        select = load_selector()
        tickers = ["A", "B", "C", "D", "E"]
        previous = {
            "A": {"pipeline_status": "ok"},
            "B": {"pipeline_status": "equity_catalog_only"},
            "C": {"pipeline_status": "ok"},
            "D": {"pipeline_status": "ok"},
        }
        chosen = select(tickers, previous, 2, today=datetime.date(2026, 10, 3))
        self.assertEqual(chosen, ["B", "E"])

    def test_cached_universe_is_bounded_and_rotates_by_day(self):
        select = load_selector()
        tickers = [f"T{i}" for i in range(10)]
        previous = {t: {"pipeline_status": "ok"} for t in tickers}
        day1 = select(tickers, previous, 3, today=datetime.date(2026, 10, 3))
        day2 = select(tickers, previous, 3, today=datetime.date(2026, 10, 4))
        self.assertEqual(len(day1), 3)
        self.assertEqual(len(day2), 3)
        self.assertNotEqual(day1, day2)
        self.assertTrue(set(day1).issubset(tickers))
        self.assertTrue(set(day2).issubset(tickers))

    def test_pipeline_fetches_only_bounded_portfolio_and_nonpriority_slices(self):
        source = RUN_PATH.read_text(encoding="utf-8")
        self.assertIn('FINSCANNER_FUNDAMENTALS_PORTFOLIO_REFRESH", "140"', source)
        self.assertIn('FINSCANNER_FUNDAMENTALS_NONPRIORITY_REFRESH", "180"', source)
        self.assertIn("portfolio_refresh = _select_nonpriority_refresh(", source)
        self.assertIn("raw_portfolio = fetch_many(portfolio_refresh, workers_override=2, retries=1", source)
        self.assertIn("raw_remainder = fetch_many(remainder_refresh, retries=0)", source)
        self.assertNotIn("raw_portfolio = fetch_many(portfolio_remainder", source)
        self.assertNotIn("raw_remainder = fetch_many(remainder_tickers", source)

    def test_slow_enrichment_lanes_have_explicit_budgets_and_stage_timers(self):
        source = RUN_PATH.read_text(encoding="utf-8")
        self.assertIn('FINSCANNER_ESEF_NONPRIORITY_REFRESH", "60"', source)
        self.assertIn('FINSCANNER_GAP_REFRESH", "80"', source)
        self.assertIn('FINSCANNER_QUARTERLY_GAP_REFRESH", "80"', source)
        self.assertIn('PIPELINE_STAGE done %s elapsed=%.1fs', source)

    def test_carried_equities_receive_latest_price_history(self):
        source = RUN_PATH.read_text(encoding="utf-8")
        self.assertIn('carried["pipeline_status"] = "equity_carried_forward_rotating"', source)
        self.assertIn('_hist = insider_price_map.get(ticker) or carried.get("price_history_1y") or []', source)
        self.assertIn('carried["current_price"] = _hist[-1].get("close")', source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
