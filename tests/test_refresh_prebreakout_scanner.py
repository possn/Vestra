import importlib.util
import math
import unittest
from datetime import date, timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("prebreakout",ROOT/"scripts/refresh_prebreakout_scanner.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class PrebreakoutDataTests(unittest.TestCase):
    def bars(self,trend=True):
        today=date.today()
        rows=[]
        for i in range(260):
            base=50+(0.075*i if trend else -0.04*i)
            wiggle=(5*math.sin(i*1.4) if 160<=i<200 else .22*math.sin(i*.4))
            c=base+wiggle
            rows.append({"date":(today-timedelta(days=259-i)).isoformat(),
                         "close":c,"high":c+(.4 if i>=220 else 1.0),
                         "low":c-(.4 if i>=220 else 1.0),"volume":100000})
        rows[-1]["volume"]=180000
        return rows

    def test_requires_200_day_ma_and_rising_alignment(self):
        self.assertIsNone(mod.scan_bars("TEST",self.bars()[:190]))
        self.assertIsNone(mod.scan_bars("TEST",self.bars(trend=False)))

    def test_real_shrinking_base_can_be_scored(self):
        rows=self.bars()
        result=mod.scan_bars("TEST",rows)
        self.assertIsNotNone(result)
        self.assertEqual(result["source"],"yahoo:daily_ohlcv")
        self.assertGreater(result["sma50"],result["sma200"])
        self.assertGreater(result["priorWidthPct"],result["widthPct"])
        self.assertIn(result["stage"],("compressão","pré-breakout","confirmado"))

    def test_stale_data_are_not_included(self):
        rows=self.bars()
        for row in rows:
            row["date"]=(date.fromisoformat(row["date"])-timedelta(days=60)).isoformat()
        self.assertIsNone(mod.scan_bars("TEST",rows))

    def test_unverified_volume_never_confirms_breakout(self):
        rows=self.bars()
        rows[-1]["volume"]=None
        result=mod.scan_bars("TEST",rows)
        self.assertIsNotNone(result)
        self.assertFalse(result["volumeConfirmed"])
        self.assertNotEqual(result["stage"],"confirmado")

if __name__=="__main__":
    unittest.main()
