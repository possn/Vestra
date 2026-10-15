"""Prove the initial historical feed is exactly derived from an archived scan."""
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
INDEX=ROOT/"data/prebreakout-observations.json"
SOURCE=ROOT/"data/prebreakout-history/2026/slots/2026-10-15-slot1.json"

class PublishedObservationProvenance(unittest.TestCase):
 def test_bootstrap_matches_immutable_slot(self):
  index=json.loads(INDEX.read_text(encoding="utf-8"))
  source=json.loads(SOURCE.read_text(encoding="utf-8"))
  self.assertEqual(index["schema"],"vestra_prebreakout_observations_v1")
  self.assertIs(index["historical_only"],True)
  self.assertEqual(index["slots_considered"],1)
  self.assertEqual(source["scan_slot_utc"],1)
  expected={(s["ticker"],s["stage"],s["score"],s["date"]) for s in source["signals"]}
  actual={(s["ticker"],s["stage"],s["score"],s["signal_date"]) for s in index["observations"]}
  self.assertEqual(actual,expected)
  for row in index["observations"]:
   self.assertIs(row["current"],False)
   self.assertEqual(row["scan_slot_utc"],source["scan_slot_utc"])
   self.assertEqual(row["observed_at"],source["generated_at"])
if __name__=="__main__":
 unittest.main()
