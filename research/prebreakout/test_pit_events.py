#!/usr/bin/env python3
"""Deterministic regression tests for the offline point-in-time labeler."""
import unittest
from datetime import date, timedelta
from pit_events import breakout_outcome, purged_chronological_indices


def sample(n=55):
    first=date(2025,1,1)
    return [{"date":(first+timedelta(days=i)).isoformat(),
             "open":99.5,"high":101,"low":99,"close":100,"volume":1000}
            for i in range(n)]


class PointInTimeTests(unittest.TestCase):
    def test_future_event_needs_mature_horizon(self):
        bars=sample(32)
        bars[31].update(open=100,high=105,low=99,close=104,volume=2000)
        self.assertEqual(breakout_outcome(bars,30,102,5)["status"],"pending")
        bars+=sample(4)  # dates reset: must reject non-monotonic histories
        with self.assertRaises(ValueError):
            breakout_outcome(bars,30,102,5)

    def test_confirmed_only_with_verified_20_prior_volume(self):
        bars=sample()
        bars[31].update(open=100,high=105,low=99,close=104,volume=2000)
        result=breakout_outcome(bars,30,102,5)
        self.assertEqual(result["status"],"confirmed")
        self.assertTrue(result["horizon_matured"])
        bars[20]["volume"]=0
        self.assertEqual(breakout_outcome(bars,30,102,5)["status"],"unverified_volume")

    def test_weak_close_is_not_breakout(self):
        bars=sample()
        bars[31].update(open=100,high=105,low=99,close=101.2,volume=2000)
        self.assertEqual(breakout_outcome(bars,30,100,5)["status"],"not_confirmed")

    def test_reject_invalid_prices(self):
        bars=sample()
        bars[8]["low"]=105
        with self.assertRaises(ValueError):
            breakout_outcome(bars,30,100,5)

    def test_purge_overlapping_labels_and_embargo(self):
        events=[
          {"signal_date":"2025-01-01","signal_session":0,"label_end_session":8},
          {"signal_date":"2025-01-10","signal_session":10,"label_end_session":27},
          {"signal_date":"2025-02-01","signal_session":30,"label_end_session":50},
        ]
        got=purged_chronological_indices(events,"2025-02-01","2025-03-01",5)
        self.assertEqual(got["test"],[2])
        self.assertEqual(got["train"],[0])
        self.assertNotIn(1,got["train"])


if __name__=="__main__":
    unittest.main()
