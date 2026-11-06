"""Prospective validation exclusion accounting; never backfill legacy outcomes."""
import datetime as dt
import unittest

from scripts.opportunity_forward_validation import outcome_exclusion_reasons


class OutcomeExclusionReasonTests(unittest.TestCase):
    @staticmethod
    def snapshot(date="2026-08-01"):
        return {"date": date, "observations": {
            name: {"opportunity_score": 80}
            for name in ("OK", "LEGACY", "BAD", "ACTION", "OTHER", "MISSING")
        }}

    @staticmethod
    def result(name, **fields):
        return {"cohort_date": "2026-08-01", "horizon_days": 28,
                "ticker": name, "return_pct": 3.0, **fields}

    def test_disjoint_reasons_match_frozen_matured_universe(self):
        outcomes = [
            self.result("OK", validation_eligible=True),
            self.result("LEGACY"),
            self.result("BAD", validation_eligible=True, return_pct=None),
            self.result("ACTION", validation_eligible=False,
                        corporate_action_unresolved=True),
            self.result("OTHER", validation_eligible=False),
        ]
        # A legacy duplicate and an outcome absent from the frozen cohort must
        # not increase eligible sample or exclusion counts.
        outcomes.append(self.result("LEGACY"))
        outcomes.append(self.result("ALIEN", validation_eligible=True))
        audit = outcome_exclusion_reasons(
            dt.date(2026, 9, 1), [self.snapshot()], outcomes, 28
        )
        self.assertEqual(audit["expected_observations"], 6)
        self.assertEqual(audit["recorded_observations"], 5)
        self.assertEqual(audit["missing_observations"], 1)
        self.assertEqual(audit["duplicate_records_ignored"], 1)
        self.assertEqual(audit["unvalidated_recorded_observations"], 4)
        self.assertEqual(audit["exclusion_reasons"], {
            "eligible": 1,
            "legacy_missing_eligibility": 1,
            "invalid_return": 1,
            "unresolved_corporate_action": 1,
            "explicitly_ineligible_other": 1,
        })
        self.assertEqual(sum(audit["exclusion_reasons"].values()), 5)
        self.assertEqual(audit["classification"], "diagnostic_only_no_backfill")

    def test_future_cohorts_and_mismatched_horizons_do_not_count(self):
        audit = outcome_exclusion_reasons(
            dt.date(2026, 8, 15), [self.snapshot()],
            [self.result("OK", validation_eligible=True)], 28
        )
        self.assertEqual(audit["recorded_observations"], 0)
        self.assertEqual(audit["expected_observations"], 0)
        audit = outcome_exclusion_reasons(
            dt.date(2026, 9, 1), [self.snapshot()],
            [dict(self.result("OK", validation_eligible=True), horizon_days=84)], 28
        )
        self.assertEqual(audit["missing_observations"], 6)
        self.assertEqual(audit["recorded_observations"], 0)

    def test_invalid_numeric_return_does_not_count_as_eligible(self):
        rows = [self.result("OK", validation_eligible=True, return_pct=float("nan"))]
        audit = outcome_exclusion_reasons(
            dt.date(2026, 9, 1), [self.snapshot()], rows, 28
        )
        self.assertEqual(audit["exclusion_reasons"]["invalid_return"], 1)
        self.assertEqual(audit["exclusion_reasons"]["eligible"], 0)


if __name__ == "__main__":
    unittest.main()
