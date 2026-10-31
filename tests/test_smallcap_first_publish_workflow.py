from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/smallcap-prebreakout-research.yml"


class SmallcapFirstPublishContract(unittest.TestCase):
    def test_only_first_observed_feed_bypasses_code_pr_guard(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('if [ ! -f data/breakout-lab-smallcap-ohlcv-research.json ]; then', source)
        self.assertIn("echo 'defer=false' >> \"$GITHUB_OUTPUT\"", source)
        self.assertIn("python scripts/defer_main_publish_if_code_pr.py", source)
        self.assertIn("git add data/breakout-lab-smallcap-ohlcv-research.json", source)
        self.assertIn("python research/prebreakout/smallcap_ohlcv_collector.py", source)

if __name__ == "__main__":
    unittest.main()
