import sys
import unittest
from datetime import date,timedelta
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from prebreakout_forward_events import breakout_event,reconcile_pivot

class ForwardBreakoutEventTests(unittest.TestCase):
    def snapshot(self):
        return {"schema":"vestra_prebreakout_v1","generated_at":"2026-10-22T23:00:00Z",
                "signals":[{"ticker":"TEST","date":"2026-10-22","resistance":100,"signalClose":98.0,"signalPriceBasis":"yahoo_auto_adjusted_asof_publication"}]}
    def test_unknown_price_basis_refuses_classification(self):
        original=self.snapshot()
        del original["signals"][0]["signalClose"]
        row=breakout_event(original,"TEST",self.bars(),horizon=5)
        self.assertEqual(row["status"],"price_basis_unverified")
        self.assertIsNone(row["event_date"])

    def bars(self):
        start=date(2026,9,15)
        return [{"date":(start+timedelta(days=i)).isoformat(),
            "close":98.0,"high":99.0,"low":97.0,"volume":1000.0} for i in range(55)]
    def test_price_basis_adjustment_is_not_accepted_without_provenance(self):
        rows=self.bars()
        self.assertEqual(reconcile_pivot(self.snapshot()["signals"][0],rows),100)
        for row in rows:
            row["close"]*=0.5
            row["high"]*=0.5
            row["low"]*=0.5
        self.assertEqual(breakout_event(self.snapshot(),"TEST",rows)["status"],"price_basis_unverified")

    def test_small_dividend_like_revision_does_not_pass_rounding_guard(self):
        rows=self.bars()
        for row in rows:
            row["close"]*=0.9995
            row["high"]*=0.9995
            row["low"]*=0.9995
        self.assertIsNone(reconcile_pivot(self.snapshot()["signals"][0],rows))
        self.assertEqual(breakout_event(self.snapshot(),"TEST",rows)["status"],"price_basis_unverified")

    def test_rounded_adjusted_close_reconciles(self):
        rows=self.bars()
        signal=self.snapshot()["signals"][0]
        signal["signalClose"]=98.00001
        self.assertAlmostEqual(reconcile_pivot(signal,rows),100,places=3)

    def test_confirmed_strong_breakout_after_publication(self):
        rows=self.bars()
        item=next(row for row in rows if row["date"]=="2026-10-24")
        item.update(close=102.0,high=102.5,low=99.5,volume=2000.0)
        out=breakout_event(self.snapshot(),"TEST",rows,horizon=5)
        self.assertEqual(out["status"],"confirmed")
        self.assertEqual(out["event_date"],"2026-10-24")
        self.assertTrue(out["horizon_matured"])
    def test_confirmed_before_window_maturity_not_full_horizon(self):
        rows=self.bars()[:41]
        next(row for row in rows if row["date"]=="2026-10-24").update(
            close=102.0,high=102.5,low=99.5,volume=2000.0)
        out=breakout_event(self.snapshot(),"TEST",rows,horizon=20)
        self.assertEqual(out["status"],"confirmed")
        self.assertFalse(out["horizon_matured"])

    def test_durability_fails_pivot_after_confirmed_breakout(self):
        rows=self.bars()
        breakout=next(row for row in rows if row["date"]=="2026-10-24")
        breakout.update(close=102.0,high=102.5,low=99.5,volume=2000.0)
        result=breakout_event(self.snapshot(),"TEST",rows[:46],horizon=5)
        self.assertEqual(result["status"],"confirmed")
        self.assertTrue(result["durability"]["3"]["status"]=="observed")
        self.assertFalse(result["durability"]["3"]["held_pivot"])
        self.assertFalse(result["durability"]["5"]["held_pivot"])
        self.assertTrue(result["durability"]["10"]["status"]=="pending")

    def test_prepublication_move_does_not_count(self):
        rows=self.bars()
        item=next(row for row in rows if row["date"]=="2026-10-21")
        item.update(close=102.0,high=102.5,low=99.5,volume=2000.0)
        self.assertNotEqual(breakout_event(self.snapshot(),"TEST",rows,horizon=5)["status"],"confirmed")
    def test_unconfirmed_requires_complete_horizon(self):
        rows=self.bars()
        self.assertEqual(breakout_event(self.snapshot(),"TEST",rows[:40],horizon=20)["status"],"pending")
        self.assertEqual(breakout_event(self.snapshot(),"TEST",rows,horizon=5)["status"],"not_confirmed")
    def test_weak_close_or_missing_volume_rejected(self):
        rows=self.bars()
        item=next(row for row in rows if row["date"]=="2026-10-24")
        item.update(close=101.0,high=104.0,low=98.0,volume=2000.0)
        self.assertNotEqual(breakout_event(self.snapshot(),"TEST",rows,horizon=5)["status"],"confirmed")
        item["volume"]=float("nan")
        with self.assertRaises(ValueError):
            breakout_event(self.snapshot(),"TEST",rows)

if __name__=="__main__":
    unittest.main()
