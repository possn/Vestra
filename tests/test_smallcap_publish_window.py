"""A code PR cannot indefinitely suppress genuine smallcap research publication."""
import datetime
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from defer_main_publish_if_code_pr import smallcap_publication_overdue

UTC=datetime.timezone.utc
SCHEMA="vestra_breakout_lab_smallcap_ohlcv_research_v1"

class SmallcapPublishWindowTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime.datetime(2026,11,9,12,tzinfo=UTC)

    def previous(self,delta_hours):
        return {"schema":SCHEMA,"generated_at":(
            self.now-datetime.timedelta(hours=delta_hours)).isoformat()}

    def test_recent_real_publication_preserves_code_pr_protection(self):
        self.assertFalse(smallcap_publication_overdue(self.previous(2),self.now,24))
        self.assertFalse(smallcap_publication_overdue(self.previous(24),self.now,24))

    def test_overdue_publication_can_proceed_without_pr_freeze(self):
        self.assertTrue(smallcap_publication_overdue(self.previous(24.01),self.now,24))
        self.assertTrue(smallcap_publication_overdue(self.previous(72),self.now,24))

    def test_missing_invalid_or_future_provenance_does_not_freeze(self):
        for prior in ({},{"schema":"not_smallcap","generated_at":self.now.isoformat()},
                      {"schema":SCHEMA,"generated_at":"2026-11-07T00:00:00"},
                      {"schema":SCHEMA,"generated_at":"bad"},
                      {"schema":SCHEMA,"generated_at":(
                          self.now+datetime.timedelta(hours=1)).isoformat()}):
            with self.subTest(prior=prior):
                self.assertTrue(smallcap_publication_overdue(prior,self.now,24))

    def test_utc_offsets_and_clock_boundary(self):
        other=self.now.astimezone(datetime.timezone(datetime.timedelta(hours=1)))
        self.assertFalse(smallcap_publication_overdue(
            {"schema":SCHEMA,"generated_at":other.isoformat()},self.now,24))
        with self.assertRaises(ValueError):
            smallcap_publication_overdue(self.previous(12),self.now,0)
        with self.assertRaises(ValueError):
            smallcap_publication_overdue(self.previous(12),self.now.replace(tzinfo=None),24)

    def test_scheduled_collection_budget_exceeds_four_day_capacity_floor(self):
        import re
        workflow=(ROOT/".github/workflows/smallcap-prebreakout-research.yml").read_text()
        match=re.search(r"default: '(\d+)'",workflow)
        self.assertIsNotNone(match)
        budget=int(match.group(1))
        # Four weekday runs per day; 371 current eligible names require
        # at least 24 attempts per cycle over four full days.
        self.assertGreaterEqual(budget*16,371)
        self.assertLessEqual(budget,30)
        self.assertIn("github.event.inputs.budget || '"+str(budget)+"'",workflow)
        # This is only a theoretical capacity bound, not real OHLCV coverage.

    def test_workflow_checks_previous_snapshot_not_fresh_result(self):
        workflow=(ROOT/".github/workflows/smallcap-prebreakout-research.yml").read_text()
        self.assertIn("git show HEAD:data/breakout-lab-smallcap-ohlcv-research.json",workflow)
        self.assertLess(workflow.index("Snapshot previously published research"),
                        workflow.index("Collect independent 100m-500m"))
        self.assertIn("VESTRA_SMALLCAP_PREVIOUS: /tmp/vestra-smallcap-previous.json",workflow)
        self.assertIn("--smallcap-max-staleness-hours 24",workflow)
        self.assertIn("python -m unittest discover -s tests -p 'test_smallcap_ohlcv_collector.py'",workflow)
        self.assertIn("scripts/publish_with_retry.sh origin main",workflow)

if __name__=="__main__":
    unittest.main()
