import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from prebreakout_ma_geometry_forward import GROUPS, HORIZONS, select, compare


def captured_row(ticker, ma, base, vcp, intact=True):
    return {
        "ticker": ticker, "evaluable": True, "last_session": "2026-11-22",
        "geometry_shadow": {"base_width_pass": base, "contractions_pass": vcp},
        "research_prebreakout_lineage": {"unbroken_prebreakout_position": intact},
        "ma_structure_shadow": {
            "status": "measured", "price_order_pass": ma,
            "three_slopes_rising": True, "all_pass": ma,
            "research_only_no_eligibility_or_score_effect": True,
        },
        "asof_base_price_anchor": {
            "schema": "vestra_prebreakout_asof_base_anchor_v1",
            "session": "2026-11-22", "adjusted_close": 100,
            "adjusted_pivot_high": 110, "window_bars": 40,
            "reference_bars": 39, "historical_adjustment_factor_verified": False,
            "research_only_no_eligibility_or_score_effect": True,
        },
    }


def write_slot(root, day, rows):
    folder = root / "2026" / "slots"
    folder.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "vestra_prebreakout_v1",
        "generated_at": day + "T08:20:00+00:00",
        "scan_slot_utc": 1,
        "research_observations": {
            "point_in_time_capture_not_historical_reconstruction": True,
            "rows": rows,
        },
    }
    (folder / (day + "-slot1.json")).write_text(json.dumps(payload))


class IndependentMAForwardTests(unittest.TestCase):
    def test_first_capture_freezes_all_four_arms_and_does_not_select_later_improvement(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            write_slot(root, "2026-11-23", [
                captured_row("A", True, True, True),
                captured_row("B", False, True, True),
                captured_row("C", True, False, True),
                captured_row("D", False, False, False),
            ])
            write_slot(root, "2026-11-24", [captured_row("B", True, True, True)])
            selected = select(root)
            self.assertEqual(len(GROUPS), 4)
            self.assertEqual([len(selected["groups"][g]) for g in GROUPS], [1, 1, 1, 1])
            self.assertEqual(selected["groups"]["geometry_pass_ma_fail"][0]["ticker"], "B")
            self.assertEqual(selected["groups"]["geometry_pass_ma_pass"][0]["ticker"], "A")

    def test_reports_capture_readiness_before_and_after_first_instrumented_slot(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            empty = select(root)
            self.assertEqual(empty["capture_readiness"], "awaiting_first_instrumented_scan")
            self.assertEqual(empty["instrumented_slots_observed"], 0)
            self.assertEqual(compare(empty, {})["evidence_readiness"],
                             "awaiting_first_instrumented_scan")
            write_slot(root, "2026-11-23", [captured_row("A", True, False, False)])
            captured = select(root)
            self.assertEqual(captured["instrumented_slots_observed"], 1)
            self.assertEqual(captured["instrumented_evaluable_rows_observed"], 1)
            self.assertEqual(captured["capture_readiness"], "captured_prospective_groups")
            self.assertEqual(captured["latest_instrumented_capture"],
                             "2026-11-23T08:20:00+00:00")
            report = compare(captured, {})
            self.assertEqual(report["evidence_readiness"],
                             "captured_awaiting_first_matured_outcome")
            self.assertEqual(report["selected_tickers_total"], 1)
            self.assertEqual(report["matured_5_session_evaluable"], 0)

    def test_instrumented_but_invalid_anchor_is_not_confused_with_missing_schema(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            invalid = captured_row("A", True, False, False)
            invalid["asof_base_price_anchor"]["session"] = "2026-11-25"
            write_slot(root, "2026-11-23", [invalid])
            selected = select(root)
            self.assertEqual(selected["capture_readiness"],
                             "awaiting_complete_anchored_observation")
            self.assertEqual(selected["instrumented_slots_observed"], 1)
            self.assertEqual(compare(selected, {})["evidence_readiness"],
                             "awaiting_complete_anchored_observation")

    def test_missing_legacy_shadow_is_unknown_not_reconstructed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            older = captured_row("LEGACY", True, True, True)
            del older["ma_structure_shadow"]
            write_slot(root, "2026-11-23", [older])
            selected = select(root)
            self.assertEqual(sum(len(x) for x in selected["groups"].values()), 0)
            self.assertEqual(selected["excluded_reasons"]["missing_matched_capture"], 1)

    def test_missing_prices_never_create_false_negative_or_probability(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            write_slot(root, "2026-11-23", [captured_row("A", True, True, True)])
            results = compare(select(root), event_prices={})
            cell = results["groups"]["geometry_pass_ma_pass"]["by_horizon"]["5"]
            self.assertEqual(cell["confirmed_matured"], 0)
            self.assertEqual(cell["not_confirmed_matured"], 0)
            self.assertEqual(cell["unknown_pending_or_unverified"], 1)
            self.assertEqual(cell["unknown_reasons"], {"independent_ohlcv_unavailable": 1})
            self.assertIsNone(cell["observed_confirmed_fraction_descriptive"])
            self.assertIsNone(results["calibrated_probability"])
            self.assertEqual(list(HORIZONS), [5, 10, 20, 60])

    def test_future_or_corrupt_anchor_cannot_enter_arm(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            a = captured_row("A", True, True, True)
            a["asof_base_price_anchor"]["session"] = "2026-11-25"
            b = captured_row("B", True, True, True)
            b["ma_structure_shadow"]["all_pass"] = False
            write_slot(root, "2026-11-23", [a, b])
            selected = select(root)
            self.assertEqual(sum(len(x) for x in selected["groups"].values()), 0)
            self.assertEqual(selected["excluded_reasons"]["invalid_anchor_values"], 1)
            self.assertEqual(selected["excluded_reasons"]["invalid_ma_capture"], 1)

    def test_no_capture_arms_are_explicitly_empty(self):
        with tempfile.TemporaryDirectory() as td:
            selected = select(Path(td))
            result = compare(selected, None)
            self.assertEqual(set(result["groups"]), set(GROUPS))
            self.assertTrue(all(v["selected_tickers"] == 0 for v in result["groups"].values()))
            self.assertTrue(all(v["by_horizon"]["20"]["matured_coverage"] is None
                                for v in result["groups"].values()))


if __name__ == "__main__":
    unittest.main()
