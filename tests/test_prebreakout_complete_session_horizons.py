#!/usr/bin/env python3
"""Regression tests for complete benchmark-aligned forward sessions."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from prebreakout_forward_evaluation import evaluate

def series(dates):
    return [{"date":d,"close":100+i} for i,d in enumerate(dates)]

SESSIONS=["2026-10-12","2026-10-13","2026-10-14","2026-10-15",
          "2026-10-16","2026-10-19","2026-10-20","2026-10-21"]

class CompleteSessionHorizonTests(unittest.TestCase):
    def test_missing_middle_bar_does_not_stretch_five_sessions(self):
        benchmark=series(SESSIONS)
        asset=[x for x in series(SESSIONS) if x["date"]!="2026-10-15"]
        value=evaluate({"date":"2026-10-12","ticker":"TEST"},asset,benchmark,(5,))
        self.assertEqual(value["entry"],"2026-10-13")
        self.assertIsNone(value["results"][5])

    def test_missing_first_entry_does_not_shift_entry(self):
        benchmark=series(SESSIONS)
        asset=[x for x in series(SESSIONS) if x["date"]!="2026-10-13"]
        value=evaluate({"date":"2026-10-12","ticker":"TEST"},asset,benchmark,(5,))
        self.assertEqual(value["entry"],"2026-10-13")
        self.assertIsNone(value["results"][5])

    def test_complete_benchmark_window_evaluates(self):
        value=evaluate({"date":"2026-10-12","ticker":"TEST"},
                       series(SESSIONS),series(SESSIONS),(5,))
        self.assertEqual(value["results"][5]["exit"],"2026-10-20")
        self.assertAlmostEqual(value["results"][5]["excess_return"],0)

    def test_later_complete_window_can_be_reported_only_if_complete(self):
        benchmark=series(SESSIONS)
        asset=[x for x in series(SESSIONS) if x["date"]!="2026-10-21"]
        value=evaluate({"date":"2026-10-12","ticker":"TEST"},asset,benchmark,(5,6))
        self.assertIsNotNone(value["results"][5])
        self.assertIsNone(value["results"][6])

if __name__ == "__main__":
    unittest.main()
