import importlib.util
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("smallcap_health", ROOT / "scripts/check_smallcap_publication.py")
health = importlib.util.module_from_spec(spec)
spec.loader.exec_module(health)


class SmallcapPublishedHealthTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 9, 21, 40, tzinfo=timezone.utc)
        self.report = {
            "schema": "vestra_breakout_lab_smallcap_ohlcv_research_v1",
            "generated_at": (self.now - timedelta(hours=7)).isoformat(),
            "universe_100m_500m_count": 3,
            "evaluable_ohlcv": 1,
            "distinct_tickers_observed": 2,
            "not_observed": 1,
            "observations": [
                {"ticker": "A", "status": "evaluable_ohlcv"},
                {"ticker": "B", "status": "invalid_ohlcv"},
            ],
        }

    def test_healthy_and_exact_age_limit(self):
        self.assertEqual(health.assess_publication(self.report, self.now)["status"], "healthy")
        self.report["generated_at"] = (self.now - timedelta(hours=8)).isoformat()
        self.assertEqual(health.assess_publication(self.report, self.now)["status"], "healthy")

    def test_stale_and_future_publications_fail_closed(self):
        self.report["generated_at"] = (self.now - timedelta(hours=8, seconds=1)).isoformat()
        self.assertEqual(health.assess_publication(self.report, self.now)["reason"],
                         "publication_age_exceeded")
        self.report["generated_at"] = (self.now + timedelta(minutes=6)).isoformat()
        self.assertEqual(health.assess_publication(self.report, self.now)["reason"],
                         "future_generated_at")
        self.report["generated_at"] = "2026-11-09T21:40:00"
        self.assertEqual(health.assess_publication(self.report, self.now)["reason"],
                         "naive_generated_at")

    def test_rollup_counters_and_unique_tickers_are_verified(self):
        cases = [
            ("evaluable_ohlcv", 2, "unreconciled_evaluable_count"),
            ("not_observed", 0, "unreconciled_unobserved_count"),
            ("distinct_tickers_observed", 1, "invalid_coverage_counts"),
            ("universe_100m_500m_count", 1, "invalid_coverage_counts"),
        ]
        for field, value, expected in cases:
            with self.subTest(field=field):
                report = {**self.report, field: value}
                self.assertEqual(health.assess_publication(report, self.now)["reason"], expected)
        report = {**self.report, "observations": [
            {"ticker": "A", "status": "evaluable_ohlcv"},
            {"ticker": "A", "status": "invalid_ohlcv"},
        ]}
        self.assertEqual(health.assess_publication(report, self.now)["reason"],
                         "duplicate_or_missing_ticker")

    def test_optional_published_rollups_must_reconcile(self):
        valid = {**self.report, "observed_incomplete": 1, "universe_coverage_pct": 33.33}
        self.assertEqual(health.assess_publication(valid, self.now)["status"], "healthy")
        for field, value, reason in [
            ("observed_incomplete", 0, "unreconciled_incomplete_count"),
            ("observed_incomplete", True, "unreconciled_incomplete_count"),
            ("universe_coverage_pct", 66.67, "unreconciled_coverage_percentage"),
            ("universe_coverage_pct", True, "unreconciled_coverage_percentage"),
        ]:
            with self.subTest(field=field, value=value):
                self.assertEqual(health.assess_publication({**valid, field: value}, self.now)["reason"], reason)

    def test_schema_is_not_assumed_current(self):
        report = {**self.report, "schema": "unknown"}
        self.assertEqual(health.assess_publication(report, self.now)["reason"], "invalid_schema")

    def test_watchdog_runs_independently_on_weekdays(self):
        workflow = (ROOT / ".github/workflows/smallcap-publication-health.yml").read_text()
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("40 9,15,21 * * 1-5", workflow)
        self.assertIn("ref: main", workflow)
        self.assertIn("scripts/check_smallcap_publication.py --max-age-hours 8", workflow)
        self.assertIn("if: always()", workflow)
        self.assertNotIn("yfinance", workflow)
        self.assertNotIn("contents: write", workflow)


if __name__ == "__main__":
    unittest.main()
