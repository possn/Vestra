import datetime as dt
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "vestra_score_forward_peer_shadow",
    ROOT / "scripts" / "score_forward_validation.py",
)
mod = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(mod)


class ScorePeerShadowForwardValidationTests(unittest.TestCase):
    def test_snapshot_records_peer_shadow_candidate_without_replacing_production(self):
        rows = {
            "AAA": {
                "current_price": 100,
                "score": 72,
                "score_model": "bank",
                "sector": "Financial Services",
                "confidence_score": 80,
                "risk_gate": "clear",
            }
        }
        snap = mod.make_snapshot(dt.date(2026, 9, 19), rows, {"AAA": 78.5})
        obs = snap["observations"]["AAA"]
        self.assertEqual(obs["score"], 72)
        self.assertEqual(obs["peer_shadow_score"], 78.5)

    def test_materialised_outcome_preserves_candidate_known_at_cohort_date(self):
        snapshots = [{
            "date": "2026-08-22",
            "observations": {
                "AAA": {
                    "price": 100,
                    "score": 70,
                    "peer_shadow_score": 76,
                    "score_model": "bank",
                    "sector": "Financial Services",
                }
            },
        }]
        outcomes = []
        added = mod.materialise_outcomes(
            dt.date(2026, 9, 19),
            snapshots,
            {"AAA": {"current_price": 110}},
            outcomes,
        )
        self.assertEqual(added, 1)
        self.assertEqual(outcomes[0]["peer_shadow_score"], 76)

    def test_peer_shadow_comparison_uses_exact_same_subset(self):
        rows = []
        for cohort in range(2):
            date = (dt.date(2026, 1, 1) + dt.timedelta(days=7 * cohort)).isoformat()
            for i in range(30):
                rows.append({
                    "cohort_date": date,
                    "ticker": f"T{cohort}_{i}",
                    "score": 100 - i,
                    "peer_shadow_score": i,
                    "return_pct": i,
                    "score_model": "bank",
                    "sector": "Financial Services",
                })
        comparison = mod.peer_shadow_comparison(rows)
        self.assertEqual(comparison["eligible_n"], 60)
        self.assertEqual(comparison["cohort_count"], 2)
        self.assertLess(
            comparison["production_same_subset"]["rank_information_coefficient"], 0
        )
        self.assertGreater(
            comparison["peer_shadow"]["rank_information_coefficient"], 0
        )
        self.assertEqual(len(comparison["cohorts"]), 2)

    def test_missing_candidate_does_not_change_production_validation(self):
        rows = [
            {
                "cohort_date": "2026-08-01",
                "ticker": f"T{i}",
                "score": i,
                "return_pct": i,
                "score_model": "general",
                "sector": "Technology",
            }
            for i in range(30)
        ]
        summary = mod.summarize_horizon(rows, expected_matured_cohorts=1)
        self.assertGreater(summary["rank_information_coefficient"], 0)
        self.assertEqual(summary["peer_shadow_comparison"]["eligible_n"], 0)
        self.assertIsNone(
            summary["peer_shadow_comparison"]["peer_shadow"]["rank_information_coefficient"]
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
