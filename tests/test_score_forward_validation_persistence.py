import datetime as dt
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "score_forward_validation", ROOT / "scripts" / "score_forward_validation.py"
)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


class ScoreForwardValidationPersistenceTests(unittest.TestCase):
    def test_materialised_outcome_is_not_duplicated(self):
        today = dt.date(2026, 8, 30)
        snapshots = [{
            "date": "2026-08-02",
            "observations": {
                "AAA": {
                    "price": 100,
                    "score": 80,
                    "quality_pct": 90,
                    "sector": "Technology",
                    "score_model": "general",
                    "confidence_score": 75,
                    "risk_gate": "clear",
                }
            },
        }]
        rows = {"AAA": {"current_price": 110}}
        outcomes = []
        self.assertEqual(MOD.materialise_outcomes(today, snapshots, rows, outcomes), 1)
        self.assertEqual(len(outcomes), 1)
        self.assertAlmostEqual(outcomes[0]["return_pct"], 10.0)
        self.assertEqual(outcomes[0]["horizon_days"], 28)
        self.assertEqual(MOD.materialise_outcomes(today, snapshots, rows, outcomes), 0)
        self.assertEqual(len(outcomes), 1)

    def test_late_horizon_is_not_backfilled_with_wrong_return(self):
        today = dt.date(2026, 8, 30)
        snapshots = [{
            "date": "2026-06-01",
            "observations": {"AAA": {"price": 100, "score": 80}},
        }]
        outcomes = []
        MOD.materialise_outcomes(today, snapshots, {"AAA": {"current_price": 130}}, outcomes)
        self.assertEqual(outcomes, [])

    def test_status_depends_on_matured_cohorts_not_pooled_n(self):
        rows = []
        for i in range(120):
            rows.append({
                "cohort_date": "2026-08-02",
                "ticker": f"T{i}",
                "score": 30 + i / 2,
                "return_pct": -5 + i / 20,
                "score_model": "general",
                "sector": "Technology",
            })
        summary = MOD.summarize_horizon(rows, expected_matured_cohorts=1)
        self.assertEqual(summary["n"], 120)
        self.assertEqual(summary["cohort_count"], 1)
        self.assertEqual(summary["status"], "collecting_evidence")

    def test_multiple_cohorts_unlock_stronger_status(self):
        rows = []
        for cohort in range(8):
            date = (dt.date(2026, 1, 1) + dt.timedelta(days=7 * cohort)).isoformat()
            for i in range(30):
                rows.append({
                    "cohort_date": date,
                    "ticker": f"T{cohort}_{i}",
                    "score": 40 + i,
                    "return_pct": -3 + i / 5,
                    "score_model": "general",
                    "sector": "Technology",
                })
        summary = MOD.summarize_horizon(rows, expected_matured_cohorts=8)
        self.assertEqual(summary["cohort_count"], 8)
        self.assertEqual(summary["status"], "multiple_cohorts_available")
        self.assertGreater(summary["median_cohort_rank_ic"], 0)
        self.assertGreater(summary["median_cohort_top_minus_bottom_pct"], 0)

    def test_factor_diagnostics_are_exposed(self):
        rows = []
        for i in range(30):
            rows.append({
                "cohort_date": "2026-08-02",
                "ticker": f"T{i}",
                "score": i,
                "quality_pct": i,
                "return_pct": i * 0.5,
                "score_model": "general",
                "sector": "Technology",
            })
        summary = MOD.summarize_horizon(rows, expected_matured_cohorts=1)
        self.assertIn("quality_pct", summary["factor_rank_information_coefficient"])
        self.assertGreater(summary["factor_rank_information_coefficient"]["quality_pct"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
