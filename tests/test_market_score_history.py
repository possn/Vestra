from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = spec_from_file_location("build_market_shards_score_history", ROOT / "scripts" / "build_market_shards.py")
MODULE = module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class MarketScoreHistoryTests(unittest.TestCase):
    def test_quarter_labels_are_calendar_quarters(self):
        self.assertEqual(MODULE.score_quarter("2026-01-15"), "2026-Q1")
        self.assertEqual(MODULE.score_quarter("2026-06-30"), "2026-Q2")
        self.assertEqual(MODULE.score_quarter("2026-10-01"), "2026-Q4")
        self.assertEqual(MODULE.score_quarter("bad-date"), "")

    def test_latest_real_observation_replaces_same_quarter(self):
        history = {"ABC": [{"quarter": "2026-Q3", "date": "2026-09-20", "score": 61.0}]}
        first = MODULE.update_score_history([{"ticker": "ABC", "score": 72.4}], "2026-10-01T06:00:00Z", history)
        second = MODULE.update_score_history([{"ticker": "ABC", "score": 74.1}], "2026-12-20T06:00:00Z", first)
        self.assertEqual(second["ABC"], [
            {"quarter": "2026-Q3", "date": "2026-09-20", "score": 61.0},
            {"quarter": "2026-Q4", "date": "2026-12-20", "score": 74.1},
        ])

    def test_history_is_bounded_and_not_shipped_in_startup_index(self):
        history = {"ABC": [
            {"quarter": f"{year}-Q{quarter}", "date": f"{year}-{(quarter - 1) * 3 + 1:02d}-01", "score": 50 + quarter}
            for year in (2024, 2025, 2026) for quarter in range(1, 5)
        ]}
        updated = MODULE.update_score_history([{"ticker": "ABC", "score": 77}], "2026-10-01", history)
        self.assertEqual(len(updated["ABC"]), MODULE.SCORE_HISTORY_MAX_QUARTERS)
        self.assertEqual(updated["ABC"][-1]["quarter"], "2026-Q4")
        self.assertNotIn("score_history_quarterly", MODULE.INDEX_KEYS)

    def test_invalid_or_missing_scores_are_not_invented(self):
        updated = MODULE.update_score_history([
            {"ticker": "MISS", "score": None},
            {"ticker": "BAD", "score": 101},
            {"ticker": "OK", "score": 0},
        ], "2026-10-01", {})
        self.assertNotIn("MISS", updated)
        self.assertNotIn("BAD", updated)
        self.assertEqual(updated["OK"][0]["score"], 0.0)


if __name__ == "__main__":
    unittest.main()
