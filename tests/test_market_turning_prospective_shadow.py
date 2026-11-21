"""Prospective market-turning archive must never rewrite the future into the past."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from market_turning_prospective_shadow import freeze,matured_shadow_assessment,eligible,freeze_matured_outcomes

class ProspectiveTurningTests(unittest.TestCase):
    def test_ineligible_and_missing_data_fail_closed(self):
        from datetime import datetime, timezone
        short={"SPY":[{"date":"2026-11-20","close":100.}]}
        result=freeze(short,datetime(2026,11,21,tzinfo=timezone.utc))
        self.assertFalse(result["available"])

    def test_matured_outcome_is_immutable_under_later_price_revision(self):
        from datetime import date,timedelta,datetime,timezone
        spy=[{"date":(date(2026,1,1)+timedelta(days=i)).isoformat(),
              "close":100.-i*.1} for i in range(160)]
        day=spy[130]["date"]
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            forecast_archive=root/"forecasts"
            outcome_archive=root/"outcomes"
            forecast_archive.mkdir()
            record={
                "schema":"vestra_turning_prospective_shadow_v1",
                "observation_date":day,
                "sides":{"bottom":{
                    "model_output_uncalibrated_not_for_live_display":.4,
                    "conditional_train_prevalence":.25}},
            }
            (forecast_archive/(day+".json")).write_text(json.dumps(record))
            now=datetime(2026,11,21,tzinfo=timezone.utc)
            first=freeze_matured_outcomes(forecast_archive,spy,outcome_archive,now)
            self.assertEqual(first["total_matured_records"],1)
            immutable=(outcome_archive/(day+".json")).read_bytes()
            revised=[dict(row) for row in spy]
            for row in revised[131:]:
                row["close"]=200.
            later=freeze_matured_outcomes(forecast_archive,revised,outcome_archive,now)
            self.assertEqual((outcome_archive/(day+".json")).read_bytes(),immutable)
            self.assertEqual(first["records"],later["records"])
            self.assertFalse(later["calibrated_probability"])
            self.assertTrue(later["outcomes_append_only"])

    def test_unmatured_forecast_never_creates_outcome(self):
        from datetime import date,timedelta,datetime,timezone
        spy=[{"date":(date(2026,1,1)+timedelta(days=i)).isoformat(),
              "close":100.} for i in range(160)]
        day=spy[155]["date"]
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            root.joinpath("forecasts").mkdir()
            rec={"schema":"vestra_turning_prospective_shadow_v1",
                 "observation_date":day,"sides":{}}
            root.joinpath("forecasts",day+".json").write_text(json.dumps(rec))
            out=freeze_matured_outcomes(root/"forecasts",spy,root/"outcomes",
                                       datetime(2026,11,21,tzinfo=timezone.utc))
            self.assertEqual(out["total_matured_records"],0)
            self.assertFalse((root/"outcomes").exists())

    def test_stress_eligibility_uses_only_past(self):
        spy=[{"date":f"2020-01-{i:02d}","close":100.} for i in range(1,27)]
        self.assertFalse(eligible(spy,"bottom"))
        bars=[{"close":100.} for _ in range(125)]+[{"close":91.}]
        self.assertTrue(eligible(bars,"bottom"))
        self.assertFalse(eligible(bars,"top"))
        bars.append({"close":10000.})
        self.assertTrue(eligible(bars[:-1],"bottom"))

    def test_maturation_never_scores_unmatured_or_unfrozen(self):
        from datetime import date,timedelta
        spy=[{"date":(date(2026,1,1)+timedelta(days=i)).isoformat(),
              "close":100.-i*.1} for i in range(160)]
        mature_day=spy[130]["date"]
        unmatured_day=spy[155]["date"]
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            rec={"schema":"vestra_turning_prospective_shadow_v1",
                 "observation_date":mature_day,
                 "sides":{"bottom":{"model_output_uncalibrated_not_for_live_display":.4,
                                    "conditional_train_prevalence":.25}}}
            (root/(mature_day+".json")).write_text(json.dumps(rec))
            latest={"schema":rec["schema"],"observation_date":unmatured_day,
                    "sides":rec["sides"]}
            (root/(unmatured_day+".json")).write_text(json.dumps(latest))
            out=matured_shadow_assessment(root,spy)
            self.assertEqual(out["total_matured_records"],1)
            self.assertEqual(out["records"][0]["observation_date"],mature_day)
            self.assertFalse(out["calibrated_probability"])

if __name__=="__main__":
    unittest.main()
