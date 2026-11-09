from pathlib import Path
import sys
import unittest
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from defer_main_publish_if_code_pr import smallcap_publication_overdue
WORKFLOW=ROOT/".github/workflows/smallcap-prebreakout-research.yml"

class SmallcapFirstPublishContract(unittest.TestCase):
    def test_missing_previous_report_bypasses_code_pr_guard(self):
        source=WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("git show HEAD:data/breakout-lab-smallcap-ohlcv-research.json",source)
        self.assertIn("printf '{}' > /tmp/vestra-smallcap-previous.json",source)
        self.assertIn("VESTRA_SMALLCAP_PREVIOUS: /tmp/vestra-smallcap-previous.json",source)
        self.assertIn("--smallcap-max-staleness-hours 24",source)
        self.assertTrue(smallcap_publication_overdue(
            {},datetime(2026,11,9,tzinfo=timezone.utc),24))
        self.assertIn("git add data/breakout-lab-smallcap-ohlcv-research.json",source)
        self.assertIn("python research/prebreakout/smallcap_ohlcv_collector.py",source)

if __name__=="__main__":
    unittest.main()
