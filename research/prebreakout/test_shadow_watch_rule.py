#!/usr/bin/env python3
"""Contract tests for offline uncalibrated compression watch, synthetic inputs only."""
import tempfile
import unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
from shadow_watch_rule import evaluate_watch,record_watch

NOW=datetime(2026,10,26,12,tzinfo=timezone.utc)
def sample():
    # 65 sequential calendar dates are synthetic, NOT independently audited sessions.
    start=datetime(2026,8,1,tzinfo=timezone.utc)
    bars=[]
    for i in range(65):
        close=100+(i%10)*2 if i<45 else 116
        bars.append({"session":(start+timedelta(days=i)).date().isoformat(),
                     "open":str(close),"high":str(close+1),"low":str(close-1),
                     "close":str(close),"volume":"1000" if i<45 else "200"})
    return bars

def evaluate(rows):
    return evaluate_watch(rows,issuer_id="synthetic-id",source="synthetic-only",
                          source_available_at_utc="2026-10-05T00:00:00Z",
                          captured_at_utc=NOW.isoformat())

class WatchRuleTests(unittest.TestCase):
    def test_synthetic_pattern_is_watch_not_alpha(self):
        result=evaluate(sample())
        self.assertTrue(result["watch"])
        self.assertEqual(result["status"],"RESEARCH_WATCH_UNVALIDATED")
        self.assertNotIn("probability",result["signal"])

    def test_insufficient_returns_abstention(self):
        self.assertEqual(evaluate(sample()[:30])["status"],"INSUFFICIENT_HISTORY")

    def test_no_volume_data_rejected(self):
        rows=sample()
        del rows[-1]["volume"]
        with self.assertRaises(ValueError):
            evaluate(rows)

    def test_future_source_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_watch(sample(),issuer_id="synthetic-id",source="test",
                source_available_at_utc="2026-10-27T00:00:00Z",
                captured_at_utc=NOW.isoformat())

    def test_out_of_order_rejected(self):
        rows=sample()
        rows[-1],rows[-2]=rows[-2],rows[-1]
        with self.assertRaises(ValueError):
            evaluate(rows)

    def test_unvalidated_signal_journal_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            journal=Path(td)/"private"/"signals.jsonl"
            a=record_watch(journal,sample(),issuer_id="synthetic-id",
                source="synthetic-only",source_available_at_utc="2026-10-05T00:00:00Z",now=NOW)
            b=record_watch(journal,sample(),issuer_id="synthetic-id",
                source="synthetic-only",source_available_at_utc="2026-10-05T00:00:00Z",now=NOW)
            self.assertEqual(a["status"],"RECORDED_UNVALIDATED_SIGNAL")
            self.assertEqual(b["status"],"ALREADY_RECORDED")
            self.assertEqual(len(journal.read_text().splitlines()),1)

if __name__=="__main__":
    unittest.main()
