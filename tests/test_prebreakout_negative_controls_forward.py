import json
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from prebreakout_negative_controls_forward import archived_cases, compare

def make_slot(root, ticker, first, base, vcp, unbroken, day="2026-11-18", slot=1):
    folder = root / "2026" / "slots"
    folder.mkdir(parents=True, exist_ok=True)
    stamp = day + "T08:20:00+00:00"
    row = {"ticker": ticker, "evaluable": True, "last_session": "2026-11-17",
           "first_rejection": first,
           "geometry_shadow": {"base_width_pass": base, "contractions_pass": vcp},
           "research_prebreakout_lineage": {"unbroken_prebreakout_position": unbroken},
           "asof_base_price_anchor": {
               "schema": "vestra_prebreakout_asof_base_anchor_v1",
               "session": "2026-11-17", "adjusted_close": 100,
               "adjusted_pivot_high": 110, "window_bars": 40,
               "reference_bars": 39, "historical_adjustment_factor_verified": False,
               "research_only_no_eligibility_or_score_effect": True}}
    payload = {"schema": "vestra_prebreakout_v1", "generated_at": stamp,
               "scan_slot_utc": slot, "research_observations": {
                   "point_in_time_capture_not_historical_reconstruction": True, "rows": [row]}}
    (folder / f"{day}-slot{slot}.json").write_text(json.dumps(payload))

class NegativeControlTests(unittest.TestCase):
    def test_first_publication_and_three_groups(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            make_slot(path, "STRICT", "passed_structural_gates", True, True, True)
            make_slot(path, "MAFAIL", "moving_average_structure", True, True, True,
                      day="2026-11-19")
            make_slot(path, "CONTROL", "base_width", False, False, True,
                      day="2026-11-20")
            selection = archived_cases(path)
            self.assertEqual([len(selection["groups"][name]) for name in
                 ("canonical_structural_pass", "geometry_pass_ma_rejected",
                  "geometry_negative_control")], [1, 1, 1])
            report = compare(path, {})
            for group in report["groups"].values():
                self.assertEqual(group["by_horizon"]["5"]["unknown_pending_or_unverified"], 1)
                self.assertIsNone(group["by_horizon"]["5"]["observed_confirmed_fraction_descriptive"])
            self.assertIsNone(report["calibrated_probabilities"])

    def test_future_unverified_is_unknown_not_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            make_slot(path, "A", "moving_average_structure", True, True, True)
            report = compare(path, {"A": []})
            cell = report["groups"]["geometry_pass_ma_rejected"]["by_horizon"]["10"]
            self.assertEqual(cell["unknown_pending_or_unverified"], 1)
            self.assertEqual(cell["not_confirmed_matured"], 0)
            self.assertEqual(cell["unknown_reasons"], {"price_basis_unverified": 1})

    def test_first_valid_capture_cannot_be_replaced_by_later_stronger_setup(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            # Initial observation had no safe unbroken-pivot position.
            make_slot(path, "CHANGED", "base_width", False, False, False)
            # Later observed improvements cannot retroactively enter this cohort.
            make_slot(path, "CHANGED", "moving_average_structure", True, True, True,
                      day="2026-11-19")
            selection = archived_cases(path)
            self.assertEqual(sum(map(len, selection["groups"].values())), 0)
            self.assertEqual(selection["available_unique_first_observations"], {})

    def test_rejects_invalid_budgets(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                archived_cases(Path(directory), per_group=0)
            with self.assertRaises(ValueError):
                archived_cases(Path(directory), per_group=True)

if __name__ == "__main__":
    unittest.main()
