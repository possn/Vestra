import json
import sys
import tempfile
import unittest
from datetime import date,timedelta
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from build_prebreakout_forward_cohorts import cohorts,build,base_maturity,maturity_event_evidence,wilson_interval,purged_walkforward_folds,walkforward_holdout_returns,spy_regime_at_publication,market_regime_audit,shadow_forward_comparison

class ImmutableCohortTests(unittest.TestCase):
    def fixture(self,folder):
        path=folder/"2026"/"slots"
        path.mkdir(parents=True)
        def slot(number,day,time,stage):
            (path/f"{day}-slot{number}.json").write_text(json.dumps({
                "schema":"vestra_prebreakout_v1","generated_at":f"{day}T{time}:00Z",
                "scan_slot_utc":number,"signals":[{
                    "ticker":"AAA","date":day,"stage":stage,"score":65,
                    "source":"yahoo:daily_ohlcv"}]}))
        slot(1,"2026-10-15","08:10","compressão")
        slot(2,"2026-10-15","14:10","compressão")
        slot(3,"2026-10-15","20:10","pré-breakout")

    def bars(self):
        start=date(2026,10,15)
        return [{"date":(start+timedelta(days=i)).isoformat(),"close":100+i} for i in range(13)]

    def test_repeated_stage_does_not_expand_cohort(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp);self.fixture(path)
            cases=cohorts(path)
            self.assertEqual(len(cases),2)
            self.assertEqual([x["stage"] for x in cases],["compressão","pré-breakout"])
            self.assertEqual(cases[0]["published_at"],"2026-10-15T08:10:00+00:00")
            self.assertEqual(cases[1]["published_at"],"2026-10-15T20:10:00+00:00")

    def test_new_anchored_base_is_distinct_but_repeated_slots_do_not_duplicate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);folder=root/"2026"/"slots";folder.mkdir(parents=True)
            for day,slot,anchor in [("2026-10-15",1,"2026-09-01"),
                                    ("2026-10-15",2,"2026-09-01"),
                                    ("2026-10-20",1,"2026-10-01")]:
                (folder/f"{day}-slot{slot}.json").write_text(json.dumps({
                    "schema":"vestra_prebreakout_v1",
                    "generated_at":f"{day}T{slot*6+1:02d}:00:00Z",
                    "scan_slot_utc":slot,
                    "signals":[{"ticker":"AAA","date":day,"stage":"compressão",
                                "baseStartDate":anchor,"source":"yahoo:daily_ohlcv"}]}))
            cases=cohorts(root)
            self.assertEqual(len(cases),2)
            self.assertEqual([r["base_start_date"] for r in cases],["2026-09-01","2026-10-01"])
            summary=build(root,{},self.bars())
            self.assertEqual(summary["base_identity_coverage"],{"anchored":2,"legacy_unanchored":0})
            self.assertEqual(summary["breakout_event_evidence"]["coverage_by_horizon"]["5"]["cohorts"],2)

    def test_bad_or_future_base_anchor_cannot_create_cohort(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);folder=root/"2026"/"slots";folder.mkdir(parents=True)
            (folder/"2026-10-15-slot1.json").write_text(json.dumps({
                "schema":"vestra_prebreakout_v1","generated_at":"2026-10-15T07:00:00Z",
                "scan_slot_utc":1,"signals":[
                    {"ticker":"AAA","date":"2026-10-15","stage":"compressão",
                     "baseStartDate":"2026-10-16","source":"yahoo:daily_ohlcv"}]}))
            self.assertEqual(cohorts(root),[])

    def test_missing_prices_are_missing_not_zero_performance(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp);self.fixture(path)
            result=build(path,{},self.bars())
            self.assertEqual(result["cohort_count"],2)
            self.assertTrue(all(not case["results"] for case in result["outcomes"]))
            self.assertEqual(result["stage_evidence"]["stages"]["compressão"]["5"]["n"],0)

    def test_future_only_post_publication_adjusted_closes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp);self.fixture(path)
            bars=self.bars()
            result=build(path,{"AAA":bars},[{"date":r["date"],"close":100} for r in bars])
            self.assertEqual(result["cohort_count"],2)
            self.assertEqual(result["outcomes"][0]["entry"],"2026-10-16")
            self.assertEqual(result["stage_evidence"]["stages"]["compressão"]["5"]["n"],1)
            self.assertNotIn("hit_rate",result["stage_evidence"]["stages"]["compressão"]["5"])

    def test_age_evidence_uses_calendar_days_and_explicit_denominators(self):
        anchored={"base_start_date":"2026-09-01","signal_date":"2026-10-15"}
        self.assertEqual(base_maturity(anchored),"developing_28_to_84d")
        self.assertEqual(base_maturity({"base_start_date":None,"signal_date":"2026-10-15"}),"unverified")
        cases=[anchored,{"base_start_date":None,"signal_date":"2026-10-15"}]
        events=[
            {"base_maturity":"developing_28_to_84d","horizon_sessions":5,"status":"confirmed"},
            {"base_maturity":"unverified","horizon_sessions":5,"status":"gapped_ohlcv"}]
        evidence=maturity_event_evidence(events,cases)
        self.assertEqual(evidence["age_unit"],"calendar_days")
        developing=evidence["groups"]["developing_28_to_84d"]["by_horizon"]["5"]
        self.assertEqual(developing["evaluable"],1)
        self.assertIsNone(developing["breakout_probability"])
        missing=evidence["groups"]["unverified"]["by_horizon"]["5"]
        self.assertEqual(missing["pending_or_unverified"],1)
        self.assertEqual(missing["evaluable"],0)

    def test_wilson_boundaries_and_small_sample_abstention(self):
        self.assertIsNone(wilson_interval(0,0))
        self.assertEqual(wilson_interval(0,30)["lower"],0)
        self.assertEqual(wilson_interval(30,30)["upper"],1)
        self.assertLess(wilson_interval(15,30)["lower"],0.5)
        self.assertGreater(wilson_interval(15,30)["upper"],0.5)
        cases=[{"base_start_date":"2026-09-01","signal_date":"2026-10-15"} for _ in range(30)]
        group="developing_28_to_84d"
        sparse=[{"base_maturity":group,"horizon_sessions":5,
                 "status":"confirmed","horizon_matured":False} for _ in range(30)]
        result=maturity_event_evidence(sparse,cases)["groups"][group]["by_horizon"]["5"]
        self.assertEqual(result["confirmed"],30)
        self.assertEqual(result["matured_evaluable"],0)
        self.assertIsNone(result["wilson_95_descriptive"])
        events=[{"base_maturity":group,"horizon_sessions":5,
                 "status":"confirmed" if i<15 else "not_confirmed",
                 "horizon_matured":True} for i in range(30)]
        mature=maturity_event_evidence(events,cases)["groups"][group]["by_horizon"]["5"]
        self.assertEqual(mature["matured_evaluable"],30)
        self.assertFalse(mature["evidence_ready"])
        self.assertEqual(mature["observed_breakout_fraction"],0.5)
        self.assertIsNone(mature["wilson_95_descriptive"])
        self.assertFalse(mature["independence_verified"])
        self.assertEqual(mature["independence_reason"],"correlated_ticker_and_market_cohorts_not_adjusted")
        inadequate=maturity_event_evidence(events[:20],cases)["groups"][group]["by_horizon"]["5"]
        self.assertFalse(inadequate["evidence_ready"])
        self.assertIsNone(inadequate["observed_breakout_fraction"])

    def test_walkforward_purge_preserves_future_test_and_abstains_from_alpha_claims(self):
        cases=[{"ticker":f"T{i:02d}","stage":"compressão",
                "published_at":(date(2026,1,1)+timedelta(days=10*i)).isoformat()+"T08:00:00Z"}
               for i in range(18)]
        plan=purged_walkforward_folds(cases)
        self.assertFalse(plan["out_of_sample_validated"])
        self.assertEqual(plan["embargo_calendar_days"],42)
        self.assertTrue(plan["folds"])
        for fold in plan["folds"]:
            self.assertLess(fold["train_before"],fold["test_from"])
            self.assertGreater(fold["train_cohorts"],0)
            self.assertGreater(fold["test_cohorts"],0)
            self.assertFalse(fold["outcomes_computed"])
        self.assertEqual(purged_walkforward_folds([])["folds"],[])
        with self.assertRaises(ValueError):
            purged_walkforward_folds(cases,embargo_days=10)

    def test_holdout_returns_use_test_only_and_label_cost_as_scenario(self):
        cases=[{"ticker":f"T{i:02d}","stage":"compressão",
                "published_at":(date(2026,1,1)+timedelta(days=i*14)).isoformat()+"T08:00:00Z"}
               for i in range(12)]
        outcomes=[{"results":{5:{"return":.10,"spy_return":.03,"excess_return":.07}}}
                  for _ in cases]
        plan=purged_walkforward_folds(cases)
        summary=walkforward_holdout_returns(cases,outcomes,plan,cost_bps=25)
        self.assertFalse(summary["out_of_sample_alpha_validated"])
        self.assertTrue(summary["cost_is_assumption"])
        self.assertTrue(summary["folds"])
        first=summary["folds"][0]["by_horizon"]["5"]
        self.assertEqual(first["evaluated"],first["test_cohorts"])
        self.assertAlmostEqual(first["mean_excess_after_scenario_cost"],.0675)
        self.assertEqual(first["net_excess_positive"],first["evaluated"])
        self.assertIsNone(first["outperformance_probability"])
        self.assertEqual(summary["folds"][0]["by_horizon"]["20"]["evaluated"],0)
        self.assertIsNone(summary["folds"][0]["by_horizon"]["20"]["mean_excess_after_scenario_cost"])
        with self.assertRaises(ValueError):
            walkforward_holdout_returns(cases,outcomes[:-1],plan)

    def test_inconsistent_excess_returns_are_not_counted_as_success(self):
        cases=[{"ticker":f"Q{i}","stage":"compressão",
                "published_at":(date(2026,1,1)+timedelta(days=14*i)).isoformat()+"T08:00:00Z"}
               for i in range(12)]
        plan=purged_walkforward_folds(cases)
        outcomes=[{"results":{5:{"return":.1,"spy_return":.03,
                                 "excess_return":.70}}} for _ in cases]
        report=walkforward_holdout_returns(cases,outcomes,plan)
        first=report["folds"][0]["by_horizon"]["5"]
        self.assertEqual(first["evaluated"],0)
        self.assertEqual(first["missing"],first["test_cohorts"])
        self.assertEqual(first["net_excess_positive"],0)
        self.assertIsNone(first["net_excess_hit_fraction_descriptive"])

    def test_regime_uses_only_prepublication_spy_and_unknown_if_stale(self):
        start=date(2026,1,1)
        bars=[{"date":(start+timedelta(days=i)).isoformat(),"close":100+i} for i in range(22)]
        published="2026-01-22T08:00:00Z"
        self.assertEqual(spy_regime_at_publication(published,bars),"positive_spy_20d")
        future=[*bars,{"date":"2026-01-22","close":1},{"date":"2026-01-23","close":2}]
        self.assertEqual(spy_regime_at_publication(published,future),"positive_spy_20d")
        self.assertEqual(spy_regime_at_publication("2026-03-01T08:00:00Z",bars),"unknown")
        self.assertEqual(spy_regime_at_publication(published,bars[:15]),"unknown")
        cases=[{"market_regime_at_publication":"positive_spy_20d"}]
        outcomes=[{"results":{5:{"return":.1,"spy_return":.03,"excess_return":.07}}}]
        report=market_regime_audit(cases,outcomes)
        self.assertEqual(report["groups"]["positive_spy_20d"]["by_horizon"]["5"]["positive_net_excess"],1)
        self.assertFalse(report["probability_calibrated"])

    def test_shadow_comparison_avoids_rolling_base_pseudoreplication(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);folder=root/"2026"/"slots";folder.mkdir(parents=True)
            for day,anchor in [("2026-10-15","2026-09-01"),("2026-10-16","2026-09-02")]:
                (folder/f"{day}-slot1.json").write_text(json.dumps({
                    "schema":"vestra_prebreakout_v1","generated_at":f"{day}T07:00:00Z",
                    "scan_slot_utc":1,"signals":[],
                    "quality_shadow_cases":{"records":[{
                        "ticker":"AAA","stage":"pré-breakout","date":day,
                        "baseStartDate":anchor,"strict_eligible":False,
                        "legacy_eligible":True,"source":"yahoo:daily_ohlcv",
                        "signalPriceBasis":"yahoo_auto_adjusted_asof_publication",
                        "resistance":100,"signalClose":99}]}}))
            result=shadow_forward_comparison(root,None)
            self.assertEqual(result["groups"]["rejected_strict"]["cohorts"],1)
            self.assertEqual(result["groups"]["rejected_strict"]["by_horizon"]["5"]["unverified_or_pending"],1)
            self.assertEqual(result["groups"]["passed_strict"]["cohorts"],0)
            self.assertIsNone(result["success_probability"])
            rejected=result["groups"]["rejected_strict"]["by_horizon"]["5"]
            self.assertEqual(rejected["matured_evaluable"],0)
            self.assertEqual(rejected["matured_coverage"],0)
            self.assertIsNone(rejected["observed_breakout_fraction"])
            self.assertFalse(rejected["minimum_evidence_met"])
            self.assertFalse(rejected["selection_effect_validated"])
            for window in ("3","5","10"):
                self.assertEqual(rejected["durability"][window]["return_evaluable"],0)
                self.assertEqual(rejected["durability"][window]["joint_outcome_evaluable"],0)
                self.assertEqual(rejected["durability"][window]["joint_outcome_missing_return"],0)
                self.assertIsNone(rejected["durability"][window]["joint_outcome_coverage"])
                self.assertIsNone(rejected["durability"][window]["joint_outcome_fraction_descriptive"])
                self.assertTrue(rejected["durability"][window]["joint_outcome_counts_consistent"])
                self.assertFalse(rejected["durability"][window]["joint_outcome_fraction_is_probability"])
                for field in ("held_positive","held_nonpositive","lost_positive","lost_nonpositive"):
                    self.assertEqual(rejected["durability"][window][field],0)
                self.assertIsNone(rejected["durability"][window]["mean_end_return_from_breakout"])
                self.assertIsNone(rejected["durability"][window]["gain_loss_ratio_descriptive"])
                self.assertFalse(rejected["durability"][window]["payoff_probability_calibrated"])
            for window in ("3","5","10"):
                self.assertEqual(rejected["durability"][window]["observed"],0)
                self.assertEqual(rejected["durability"][window]["held_pivot"],0)
                self.assertEqual(rejected["durability"][window]["lost_pivot"],0)

    def test_retrospective_feature_outcomes_withhold_immature_labels(self):
        from build_prebreakout_forward_cohorts import retrospective_feature_outcome_audit
        case={"ticker":"AAA","stage":"pré-breakout","published_at":"2026-01-25T12:00:00Z"}
        bars=[{"date":f"2026-01-{i:02d}","high":101+i,"low":99+i,
               "close":100+i,"volume":1000} for i in range(1,25)]
        events=[{"ticker":"AAA","stage":"pré-breakout","published_at":case["published_at"],
                 "horizon_sessions":5,"horizon_matured":False,"status":"confirmed"}]
        report=retrospective_feature_outcome_audit([case],events,{"AAA":bars},bars)
        self.assertEqual(len(report["records"]),3)
        self.assertEqual(report["records"][0]["outcome"],"pending_or_unverified")
        self.assertFalse(report["trained_model"])
        self.assertFalse(report["adjusted_history_point_in_time_verified"])

    def test_joint_durability_requires_matured_event_and_finite_return(self):
        from build_prebreakout_forward_cohorts import retrospective_feature_outcome_audit
        case={"ticker":"AAA","stage":"pré-breakout","published_at":"2026-01-25T12:00:00Z"}
        bars=[]
        ev={"ticker":"AAA","stage":"pré-breakout","published_at":case["published_at"],
            "horizon_sessions":5,"horizon_matured":True,"status":"confirmed",
            "durability":{"3":{"status":"observed","held_pivot":True,"end_return_from_breakout":0.03},
                          "5":{"status":"observed","held_pivot":False,"end_return_from_breakout":float("nan")},
                          "10":{"status":"pending"}}}
        report=retrospective_feature_outcome_audit([case],[ev],{"AAA":bars},bars)
        labels=report["records"][0]["joint_durability_outcomes"]
        self.assertEqual(labels["3"],"held_positive")
        self.assertEqual(labels["5"],"pending_or_unverified")
        self.assertEqual(labels["10"],"pending_or_unverified")
        ev["horizon_matured"]=False
        report=retrospective_feature_outcome_audit([case],[ev],{"AAA":bars},bars)
        self.assertEqual(report["records"][0]["joint_durability_outcomes"]["3"],"pending_or_unverified")

    def test_wrong_slot_never_creates_cohort(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);f=root/"2026"/"slots";f.mkdir(parents=True)
            (f/"2026-10-15-slot2.json").write_text(json.dumps({"schema":"vestra_prebreakout_v1",
                "generated_at":"2026-10-15T08:10:00Z","scan_slot_utc":2,
                "signals":[{"ticker":"FAKE","date":"2026-10-15","stage":"confirmado","source":"yahoo:daily_ohlcv"}]}))
            self.assertEqual(cohorts(root),[])

class StructuralShadowOutcomeTests(unittest.TestCase):
    def test_groups_are_prospective_and_unknown_not_false_negative(self):
        from build_prebreakout_forward_cohorts import structural_shadow_evidence
        from datetime import datetime, timezone
        stamp=datetime(2026,10,20,8,15,tzinfo=timezone.utc)
        def row(ticker,status,eligible):
            return {"ticker":ticker,"date":"2026-10-19","stage":"pré-breakout",
                "signalClose":100,"resistance":101,
                "signalPriceBasis":"yahoo_auto_adjusted_asof_publication",
                "structural_readiness_shadow":{"model":"atr_support_v1_shadow",
                    "status":status,"eligible":eligible}}
        records={("A","pré-breakout"):(stamp,row("A","research_eligible",True)),
            ("B","pré-breakout"):(stamp,row("B","research_rejected",False)),
            ("C","pré-breakout"):(stamp,row("C","research_eligible",False)),
            ("D","pré-breakout"):(stamp,row("D","unverifiable",None))}
        outcome=structural_shadow_evidence(records,None)
        groups=outcome["groups"]
        self.assertEqual(groups["research_eligible"]["cohorts"],1)
        self.assertEqual(groups["research_rejected"]["cohorts"],1)
        self.assertEqual(groups["unverifiable"]["cohorts"],2)
        for group in groups.values():
            for cell in group["by_horizon"].values():
                self.assertEqual(cell["matured_evaluable"],0)
                self.assertEqual(cell["unverified_or_pending"],group["cohorts"])
                self.assertIsNone(cell["observed_breakout_fraction_descriptive"])
                self.assertFalse(cell["minimum_evidence_met"])
                self.assertFalse(cell["probability_calibrated"])
        self.assertFalse(outcome["selection_effect_validated"])
        self.assertFalse(outcome["out_of_sample_validated"])


class DailyFocusProspectiveTests(unittest.TestCase):
    def test_one_asof_selection_per_day_and_unknown_outcomes(self):
        from build_prebreakout_forward_cohorts import daily_focus_forward_evidence
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);folder=root/"2026"/"slots";folder.mkdir(parents=True)
            for slot,hour in ((1,8),(2,14)):
                stamp=f"2026-10-15T{hour:02d}:10:00Z"
                (folder/f"2026-10-15-slot{slot}.json").write_text(json.dumps({
                    "schema":"vestra_prebreakout_v1","generated_at":stamp,
                    "scan_slot_utc":slot,
                    "daily_focus":{"status":"research_candidate","ticker":"AAA"},
                    "signals":[{"ticker":"AAA","date":"2026-10-14",
                        "stage":"pré-breakout","source":"yahoo:daily_ohlcv",
                        "signalClose":98,"resistance":100,
                        "signalPriceBasis":"yahoo_auto_adjusted_asof_publication",
                        "scanner_verified_at":stamp}]}))
            (folder/"2026-10-16-slot1.json").write_text(json.dumps({
                "schema":"vestra_prebreakout_v1",
                "generated_at":"2026-10-16T08:10:00Z","scan_slot_utc":1,
                "daily_focus":{"status":"no_qualified_setup","ticker":None},
                "signals":[]}))
            result=daily_focus_forward_evidence(root,None)
            self.assertEqual(result["archive_days"],2)
            self.assertEqual(result["days_with_verifiable_daily_pick"],1)
            self.assertEqual(result["days_without_verifiable_daily_pick"],1)
            for cell in result["by_horizon"].values():
                self.assertEqual(cell["selected"],1)
                self.assertEqual(cell["pending_or_unverifiable"],1)
                self.assertEqual(cell["evaluable"],0)
                self.assertIsNone(cell["calibrated_probability"])
                self.assertFalse(cell["minimum_sample_met"])

    def test_stale_carried_signal_cannot_be_attributed_to_current_daily_pick(self):
        from build_prebreakout_forward_cohorts import daily_focus_forward_evidence
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/"2026"/"slots";folder.mkdir(parents=True)
            (folder/"2026-10-15-slot1.json").write_text(json.dumps({
                "schema":"vestra_prebreakout_v1","generated_at":"2026-10-15T08:10:00Z",
                "scan_slot_utc":1,
                "daily_focus":{"status":"research_candidate","ticker":"AAA"},
                "signals":[{"ticker":"AAA","date":"2026-10-14",
                    "stage":"pré-breakout","source":"yahoo:daily_ohlcv",
                    "scanner_verified_at":"2026-10-13T20:10:00Z"}]}))
            result=daily_focus_forward_evidence(Path(tmp),None)
            self.assertEqual(result["days_with_verifiable_daily_pick"],0)


class DailyFocusTierEvidenceTests(unittest.TestCase):
    def test_developing_daily_pick_is_counted_separately_and_unknown_stays_unknown(self):
        from build_prebreakout_forward_cohorts import daily_focus_forward_evidence
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/"2026"/"slots";folder.mkdir(parents=True)
            stamp="2026-10-15T08:10:00Z"
            (folder/"2026-10-15-slot1.json").write_text(json.dumps({
                "schema":"vestra_prebreakout_v1","generated_at":stamp,"scan_slot_utc":1,
                "daily_focus":{"status":"research_candidate","ticker":"FORM",
                    "selection_tier":"developing_setup"},
                "signals":[{"ticker":"FORM","date":"2026-10-14","stage":"compressão",
                    "vcpConfirmed":True,"source":"yahoo:daily_ohlcv",
                    "scanner_verified_at":stamp,"resistance":100,
                    "signalClose":98,"signalPriceBasis":"yahoo_auto_adjusted_asof_publication"}]}))
            out=daily_focus_forward_evidence(Path(tmp),None)
            self.assertEqual(out["days_with_verifiable_daily_pick"],1)
            self.assertEqual(out["by_selection_tier"]["developing_setup"]["selected"],1)
            self.assertEqual(out["by_selection_tier"]["verified_prebreakout"]["selected"],0)
            self.assertEqual(out["by_horizon"]["5"]["pending_or_unverifiable"],1)
            self.assertIsNone(out["by_selection_tier"]["developing_setup"]["by_horizon"]["5"]["calibrated_probability"])

    def test_invalid_developing_tier_never_promotes_non_vcp(self):
        from build_prebreakout_forward_cohorts import daily_focus_forward_evidence
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/"2026"/"slots";folder.mkdir(parents=True)
            stamp="2026-10-15T08:10:00Z"
            (folder/"2026-10-15-slot1.json").write_text(json.dumps({
                "schema":"vestra_prebreakout_v1","generated_at":stamp,"scan_slot_utc":1,
                "daily_focus":{"status":"research_candidate","ticker":"BAD",
                    "selection_tier":"developing_setup"},
                "signals":[{"ticker":"BAD","date":"2026-10-14","stage":"compressão",
                    "vcpConfirmed":False,"source":"yahoo:daily_ohlcv",
                    "scanner_verified_at":stamp}]}))
            out=daily_focus_forward_evidence(Path(tmp),None)
            self.assertEqual(out["days_with_verifiable_daily_pick"],0)


class PriceBasisAuditTests(unittest.TestCase):
    def test_unverified_anchor_reasons_are_counted_not_failures(self):
        from build_prebreakout_forward_cohorts import build
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/"2026"/"slots";folder.mkdir(parents=True)
            (folder/"2026-10-15-slot1.json").write_text(json.dumps({
                "schema":"vestra_prebreakout_v1","generated_at":"2026-10-15T08:10:00Z",
                "scan_slot_utc":1,"signals":[{"ticker":"AAA","stage":"pré-breakout",
                    "date":"2026-10-14","source":"yahoo:daily_ohlcv",
                    "signalClose":98,"resistance":100,
                    "signalPriceBasis":"yahoo_auto_adjusted_asof_publication"}]}))
            bars=[{"date":"2026-10-14","close":97.5,"low":96,"high":99,
                   "volume":1000}]
            out=build(Path(tmp),{},[],event_prices={"AAA":bars})
            coverage=out["breakout_event_evidence"]
            audit=coverage["price_basis_audit"]["5"]
            self.assertEqual(audit["unverifiable"],1)
            self.assertEqual(audit["by_reason"],
                {"adjusted_price_revision_without_verified_factor":1})
            self.assertFalse(audit["price_factor_inferred"])
            self.assertEqual(coverage["coverage_by_horizon"]["5"]["evaluable"],0)
            self.assertEqual(coverage["coverage_by_horizon"]["5"]["by_status"]["price_basis_unverified"],1)


class AnchorProvenanceAuditTests(unittest.TestCase):
    def test_legacy_missing_basis_is_not_treated_as_failed_breakout(self):
        from build_prebreakout_forward_cohorts import build
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/"2026"/"slots";folder.mkdir(parents=True)
            for slot,ticker,with_basis in [(1,"LEGACY",False),(2,"FUTURE",True)]:
                row={"ticker":ticker,"date":"2026-10-15","stage":"compressão",
                    "source":"yahoo:daily_ohlcv"}
                if with_basis:
                    row.update(signalClose=98,resistance=100,
                        signalPriceBasis="yahoo_auto_adjusted_asof_publication")
                (folder/f"2026-10-15-slot{slot}.json").write_text(json.dumps({
                    "schema":"vestra_prebreakout_v1","scan_slot_utc":slot,
                    "generated_at":f"2026-10-15T{slot*6+2:02d}:00:00Z",
                    "signals":[row]}))
            out=build(Path(tmp),{},[],event_prices={})
            audit=out["anchor_provenance_audit"]
            self.assertEqual(audit["verifiable_archived_price_basis"],1)
            self.assertEqual(audit["legacy_missing_or_unverified_price_basis"],1)
            self.assertEqual(audit["potentially_verifiable_by_horizon"]["5"]["evaluated"],0)
            self.assertTrue(audit["potentially_verifiable_by_horizon"]["5"]["not_a_probability"])


class DailyFocusCoverageAuditTests(unittest.TestCase):
    def test_abstention_and_invalid_candidate_are_not_merged(self):
        from build_prebreakout_forward_cohorts import daily_focus_forward_evidence
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/"2026"/"slots";folder.mkdir(parents=True)
            examples=[
                ("2026-10-15",{"status":"no_qualified_setup","ticker":None},[]),
                ("2026-10-16",{"status":"research_candidate","ticker":"AAA"},
                 [{"ticker":"AAA","stage":"compressão","source":"yahoo:daily_ohlcv",
                   "scanner_verified_at":"2026-10-14T08:10:00Z"}]),
                ("2026-10-17",None,[])]
            for day,focus,signals in examples:
                feed={"schema":"vestra_prebreakout_v1",
                    "generated_at":day+"T08:10:00Z","scan_slot_utc":1,"signals":signals}
                if focus is not None:feed["daily_focus"]=focus
                (folder/(day+"-slot1.json")).write_text(json.dumps(feed))
            out=daily_focus_forward_evidence(Path(tmp),None)
            self.assertEqual(out["archive_days"],3)
            self.assertEqual(out["days_with_verifiable_daily_pick"],0)
            self.assertEqual(out["days_with_explicit_abstention_only"],1)
            self.assertEqual(out["days_with_candidate_but_no_verifiable_pick"],1)
            self.assertEqual(out["days_with_invalid_or_missing_focus_publication"],1)
            self.assertIsNone(out["by_horizon"]["5"]["calibrated_probability"])


class PostConfirmationPayoffTests(unittest.TestCase):
    def test_only_completed_durability_windows_get_gross_and_cost_scenario(self):
        from build_prebreakout_forward_cohorts import build
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/"2026"/"slots";folder.mkdir(parents=True)
            (folder/"2026-10-15-slot1.json").write_text(json.dumps({
                "schema":"vestra_prebreakout_v1","scan_slot_utc":1,
                "generated_at":"2026-10-15T08:10:00Z",
                "signals":[{"ticker":"AAA","date":"2026-10-14","stage":"compressão",
                    "source":"yahoo:daily_ohlcv","signalClose":100.0,
                    "resistance":101.0,
                    "signalPriceBasis":"yahoo_auto_adjusted_asof_publication"}]}))
            from datetime import date,timedelta
            start=date(2026,9,15)
            days=[start+timedelta(days=i) for i in range(41)]
            bars=[]
            for i,d in enumerate(days):
                close=100.0 if d.isoformat()<"2026-10-16" else 104.0
                bars.append({"date":d.isoformat(),"close":close,
                    "high":close+0.5,"low":close-0.5,
                    "volume":1000.0 if d.isoformat()<"2026-10-16" else 3000.0})
            out=build(Path(tmp),{},[],event_prices={"AAA":bars})
            dur=out["breakout_event_evidence"]["coverage_by_horizon"]["5"]["post_confirmation_durability"]["3"]
            self.assertEqual(dur["return_observations"],1)
            self.assertEqual(dur["positive_gross"],0)
            self.assertEqual(dur["positive_net_after_cost_scenario"],0)
            self.assertEqual(dur["cost_scenario_round_trip_fraction"],0.002)
            self.assertFalse(dur["execution_adjusted"])
            self.assertIsNone(dur["calibrated_probability"])


if __name__=="__main__":
    unittest.main()
