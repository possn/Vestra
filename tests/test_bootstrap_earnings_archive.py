from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from bootstrap_earnings_archive import verified_rows


class BootstrapEarningsArchiveTests(unittest.TestCase):
    def test_only_verified_eps_and_dated_rows_are_seeded(self):
        rows = [
            {"ticker": "AAA", "analyst_latest_earnings_date": "2026-09-20", "analyst_latest_eps_actual": 0.0},
            {"ticker": "BBB", "analyst_latest_earnings_date": "2026-09-20"},
            {"ticker": "CCC", "analyst_latest_earnings_date": "2026-09-20", "analyst_latest_eps_actual": None},
            {"ticker": "DDD", "analyst_latest_earnings_date": "2026-09-20", "analyst_latest_eps_actual": True},
            {"ticker": "EEE", "analyst_latest_eps_actual": 1.1},
        ]
        self.assertEqual([row["ticker"] for row in verified_rows(rows)], ["AAA"])

    def test_archive_stays_separate_from_startup_payload(self):
        workflow = (ROOT / ".github/workflows/bootstrap-earnings-archive.yml").read_text()
        self.assertIn("git add data/earnings-events.json", workflow)
        self.assertNotIn("git add data/stocks-index.json", workflow)
        self.assertIn("defer_main_publish_if_code_pr.py", workflow)
        self.assertIn("scripts/publish_with_retry.sh", workflow)


if __name__ == "__main__":
    unittest.main()
