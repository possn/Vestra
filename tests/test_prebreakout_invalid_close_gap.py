"""Do not drop corrupt daily closes and manufacture shorter MA return windows."""
import importlib.util
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("prebreakout",ROOT/"scripts/refresh_prebreakout_scanner.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class CloseHistoryIntegrityTests(unittest.TestCase):
    class Frame:
        empty=False
        def __init__(self,close):self.close=close
        def iterrows(self):
            start=datetime(2026,1,1,tzinfo=timezone.utc)
            for i in range(230):
                yield start+timedelta(days=i),{
                    "Close":self.close if i==114 else 100.0,
                    "High":101.0,"Low":99.0,"Volume":2000.0}

    def test_invalid_closes_keep_daily_session_as_explicit_gap(self):
        for malformed in (None,float("nan"),float("inf"),"not-a-price"):
            with self.subTest(value=malformed):
                bars=mod.dataframe_bars(self.Frame(malformed))
                self.assertEqual(len(bars),230)
                self.assertIsNone(bars[114]["close"])
                today=date(2026,8,20)
                self.assertFalse(mod.evaluable_recheck(bars,today))
                trace={}
                self.assertIsNone(mod.scan_bars("BAD",bars,today,audit=trace))
                self.assertEqual(trace["first_rejection"],"invalid_ohlcv_or_date")

    def test_valid_sessions_remain_available(self):
        bars=mod.dataframe_bars(self.Frame(100.0))
        self.assertEqual(len(bars),230)
        self.assertEqual(bars[114]["close"],100.0)


if __name__=="__main__":
    unittest.main()
