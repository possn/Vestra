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


if __name__ == "__main__":
    unittest.main(verbosity=2)
