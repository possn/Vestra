import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("build_market_shards", SCRIPTS / "build_market_shards.py")
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


class FundWeeklyReturnTests(unittest.TestCase):
    def test_weekly_history_uses_previous_week(self):
        row = {
            "price_history_1y": [
                {"date": "2026-09-18", "close": 100.0},
                {"date": "2026-09-25", "close": 110.0},
                {"date": "2026-10-02", "close": 121.0},
            ]
        }
        self.assertEqual(MOD.fund_weekly_return(row), 10.0)

    def test_daily_history_uses_point_nearest_seven_days_not_previous_day(self):
        row = {
            "price_history_1y": [
                {"date": "2026-09-25", "close": 100.0},
                {"date": "2026-09-29", "close": 104.0},
                {"date": "2026-09-30", "close": 106.0},
                {"date": "2026-10-01", "close": 108.0},
                {"date": "2026-10-02", "close": 110.0},
            ]
        }
        self.assertEqual(MOD.fund_weekly_return(row), 10.0)

    def test_weekly_return_fails_closed_without_roughly_week_old_point(self):
        row = {
            "price_history_1y": [
                {"date": "2026-10-01", "close": 100.0},
                {"date": "2026-10-02", "close": 101.0},
            ]
        }
        self.assertIsNone(MOD.fund_weekly_return(row))

    def test_carried_fund_aum_does_not_create_today_flow_snapshot(self):
        history = {
            "SMH": {
                "2026-09-29": {"assets": 10_000_000_000.0, "price": 600.0},
            }
        }
        rows = [{
            "ticker": "SMH",
            "quote_type": "ETF",
            "fund_total_assets": 10_000_000_000.0,
            "current_price": 630.0,
            "pipeline_status": "catalog_carried_forward",
        }]
        updated = MOD.update_fund_aum_history(rows, "2026-10-06", history)
        self.assertNotIn("2026-10-06", updated["SMH"])
        metrics = MOD.fund_flow_metrics(rows[0], updated, "2026-10-06")
        self.assertNotIn("fund_flow_1w_usd", metrics)

    def test_carried_fund_purges_untagged_same_day_snapshot(self):
        history = {
            "SMH": {
                "2026-09-29": {"assets": 10_000_000_000.0, "price": 600.0},
                "2026-10-06": {"assets": 10_000_000_000.0, "price": 630.0},
            }
        }
        rows = [{
            "ticker": "SMH",
            "quote_type": "ETF",
            "fund_total_assets": 10_000_000_000.0,
            "current_price": 630.0,
            "pipeline_status": "catalog_carried_forward",
        }]
        updated = MOD.update_fund_aum_history(rows, "2026-10-06", history)
        self.assertNotIn("2026-10-06", updated["SMH"])
        self.assertNotIn("fund_flow_1w_usd", MOD.fund_flow_metrics(rows[0], updated, "2026-10-06"))

    def test_carried_fund_keeps_explicitly_observed_same_day_snapshot(self):
        history = {
            "SMH": {
                "2026-09-29": {"assets": 10_000_000_000.0, "price": 600.0},
                "2026-10-06": {"assets": 10_500_000_000.0, "price": 630.0, "aum_observed": True},
            }
        }
        rows = [{
            "ticker": "SMH",
            "quote_type": "ETF",
            "fund_total_assets": 10_500_000_000.0,
            "current_price": 630.0,
            "pipeline_status": "catalog_carried_forward",
        }]
        updated = MOD.update_fund_aum_history(rows, "2026-10-06", history)
        self.assertIn("2026-10-06", updated["SMH"])
        self.assertTrue(updated["SMH"]["2026-10-06"]["aum_observed"])

    def test_fresh_fund_aum_creates_today_flow_snapshot(self):
        history = {
            "SMH": {
                "2026-09-29": {"assets": 10_000_000_000.0, "price": 600.0},
            }
        }
        rows = [{
            "ticker": "SMH",
            "quote_type": "ETF",
            "fund_total_assets": 10_500_000_000.0,
            "current_price": 630.0,
        }]
        updated = MOD.update_fund_aum_history(rows, "2026-10-06", history)
        self.assertIn("2026-10-06", updated["SMH"])
        self.assertTrue(updated["SMH"]["2026-10-06"]["aum_observed"])
        metrics = MOD.fund_flow_metrics(rows[0], updated, "2026-10-06")
        self.assertIn("fund_flow_1w_usd", metrics)


if __name__ == "__main__":
    unittest.main(verbosity=2)
