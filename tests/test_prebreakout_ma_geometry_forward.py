import hashlib
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
        "technical_evidence_shadow": {
            "status": "measured", "atr14_pct": 2.1,
            "volume9_to_prior40": 1.15,
        },
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

    def test_cohort_capacity_uses_precommitted_hash_tiebreak_not_alphabetical(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            tickers = [f"T{i:03d}" for i in range(40)]
            write_slot(root, "2026-11-23",
                       [captured_row(t, False, False, False) for t in tickers])
            write_slot(root, "2026-11-24",
                       [captured_row("LATER", False, False, False)])
            selected = select(root, per_group=32)
            group = selected["groups"]["geometry_fail_ma_fail"]
            actual = [c["ticker"] for c in group]
            def hash_key(t):
                return hashlib.sha256(
                    ("vestra-ma-vcp-2026-v1:" + t).encode("utf-8")
                ).hexdigest()
            expected = sorted(tickers, key=lambda t: (hash_key(t), t))[:32]
            self.assertEqual(actual, expected)
            self.assertNotEqual(actual, tickers[:32])
            self.assertNotIn("LATER", actual)
            self.assertEqual(selected["eligible_unique_first_observations"]
                             ["geometry_fail_ma_fail"], 41)
            self.assertTrue(selected["deterministic_sample_not_randomized"])

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

    def test_already_broken_baseline_is_unknown_not_future_prebreakout_success(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            write_slot(root, "2026-11-23", [
                captured_row("BROKEN", True, False, False, intact=False),
                captured_row("UNBROKEN", True, False, False, intact=True),
            ])
            selected = select(root)
            group = selected["groups"]["geometry_fail_ma_pass"]
            self.assertEqual(len(group), 2)
            self.assertEqual({x["ticker"]: x["unbroken_at_capture"] for x in group},
                             {"BROKEN": False, "UNBROKEN": True})
            report = compare(selected, {})
            arm = report["groups"]["geometry_fail_ma_pass"]
            self.assertEqual(arm["selected_tickers"], 2)
            self.assertEqual(arm["baseline_integrity"]["unbroken_prebreakout_at_capture"], 1)
            self.assertEqual(arm["baseline_integrity"]["already_broken_or_outside_pivot_at_capture"], 1)
            for horizon in HORIZONS:
                cell = arm["by_horizon"][str(horizon)]
                self.assertEqual(cell["confirmed_matured"], 0)
                self.assertEqual(cell["not_confirmed_matured"], 0)
                self.assertEqual(cell["unknown_pending_or_unverified"], 2)
                self.assertEqual(cell["unknown_reasons"],
                                 {"already_broken_or_outside_pivot_at_capture": 1,
                                  "independent_ohlcv_unavailable": 1})
            self.assertIsNone(report["calibrated_probability"])

    def test_baseline_identity_is_immutable_even_if_subsequent_capture_changes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            write_slot(root, "2026-11-23",
                       [captured_row("A", False, False, False, intact=False)])
            write_slot(root, "2026-11-24",
                       [captured_row("A", True, True, True, intact=True)])
            selected = select(root)
            case = selected["groups"]["geometry_fail_ma_fail"][0]
            self.assertFalse(case["unbroken_at_capture"])
            self.assertEqual(selected["groups"]["geometry_pass_ma_pass"], [])
            self.assertEqual(compare(selected, {})["groups"]["geometry_fail_ma_fail"]
                             ["by_horizon"]["5"]["unknown_reasons"],
                             {"already_broken_or_outside_pivot_at_capture": 1})

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

    def test_flat_fake_vcp_and_missing_volume_abstain_without_reclassifying(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            flat = captured_row("FLAT", True, True, True, intact=True)
            flat["technical_evidence_shadow"]["atr14_pct"] = 0
            flat["technical_evidence_shadow"]["volume9_to_prior40"] = None
            missing_volume = captured_row("NOVOL", True, True, True, intact=True)
            missing_volume["technical_evidence_shadow"]["volume9_to_prior40"] = None
            genuine = captured_row("VALID", True, True, True, intact=True)
            write_slot(root, "2026-11-24", [flat, missing_volume, genuine])
            v1 = select(root)
            v2 = select(root, at_risk_only=True)
            self.assertEqual(len(v1["groups"]["geometry_pass_ma_pass"]), 3)
            self.assertEqual(len(v2["groups"]["geometry_pass_ma_pass"]), 3)
            result = compare(v2, {})
            bucket = result["groups"]["geometry_pass_ma_pass"]
            self.assertEqual(bucket["selected_tickers"], 3)
            self.assertEqual(bucket["activity_quality_at_capture"]
                             ["independently_evaluable_baselines"], 1)
            self.assertEqual(bucket["activity_quality_at_capture"]["counts"], {
                "no_measurable_price_range_at_capture": 1,
                "volume_activity_unverified_at_capture": 1,
                "verified_nonflat_price_and_volume_at_capture": 1})
            self.assertEqual(bucket["by_horizon"]["5"]["unknown_reasons"], {
                "no_measurable_price_range_at_capture": 1,
                "volume_activity_unverified_at_capture": 1,
                "independent_ohlcv_unavailable": 1})
            # Historical v1 remains methodologically unmodified.
            self.assertNotIn("activity_quality_at_capture",
                             compare(v1, {})["groups"]["geometry_pass_ma_pass"])

    def test_zero_volume_is_not_technical_accumulation(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            row = captured_row("ZERO", True, True, True)
            row["technical_evidence_shadow"]["volume9_to_prior40"] = 0
            write_slot(root, "2026-11-24", [row])
            report = compare(select(root, at_risk_only=True), {})
            self.assertEqual(report["groups"]["geometry_pass_ma_pass"]
                             ["by_horizon"]["10"]["unknown_reasons"],
                             {"no_positive_volume_activity_at_capture": 1})

    def test_at_risk_v2_does_not_retrofit_v1_and_excludes_broken_baselines(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            write_slot(root, "2026-11-23", [
                captured_row("OLD", False, False, False, intact=True)])
            write_slot(root, "2026-11-24", [
                captured_row("BROKEN", True, False, False, intact=False),
                captured_row("VALID", True, False, False, intact=True),
                captured_row("OLD", False, False, False, intact=True)])
            old = select(root)
            new = select(root, at_risk_only=True)
            self.assertIn("OLD", {v["ticker"] for g in old["groups"].values() for v in g})
            self.assertEqual(new["capture_readiness"], "captured_prospective_groups")
            self.assertTrue(new["at_risk_baseline_only"])
            self.assertEqual(new["not_before_instrumented_utc"],
                             "2026-11-24T02:00:00+00:00")
            self.assertEqual(new["excluded_reasons"]["already_broken_at_first_capture"], 1)
            self.assertEqual(
                {v["ticker"] for g in new["groups"].values() for v in g},
                {"VALID", "OLD"})
            self.assertEqual(new["groups"]["geometry_fail_ma_pass"][0]
                             ["unbroken_at_capture"], True)
            summary = compare(new, {})
            self.assertEqual(summary["schema"],
                             "vestra_prebreakout_ma_geometry_at_risk_forward_v2")
            self.assertTrue(summary["baseline_prebreakout_required"])
            self.assertEqual(compare(old, {})["schema"],
                             "vestra_prebreakout_ma_geometry_forward_v1")
            self.assertEqual(summary["selected_tickers_total"], 2)
            self.assertEqual(summary["groups"]["geometry_fail_ma_pass"]
                             ["baseline_integrity"]["already_broken_or_outside_pivot_at_capture"], 0)

    def test_at_risk_v2_does_not_replace_first_eligible_capture_later(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            write_slot(root, "2026-11-24",
                       [captured_row("A", False, False, False, intact=True)])
            write_slot(root, "2026-11-25",
                       [captured_row("A", True, True, True, intact=True)])
            new = select(root, at_risk_only=True)
            self.assertEqual(new["groups"]["geometry_fail_ma_fail"][0]["ticker"], "A")
            self.assertEqual(new["groups"]["geometry_pass_ma_pass"], [])

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
