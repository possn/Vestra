"""Prospective research-only base anchors must never manufacture a verified signal."""
import copy
import json
import sys
import tempfile
import unittest
from datetime import date,timedelta
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from build_prebreakout_forward_cohorts import research_anchor_cases,research_anchor_forward_audit


class ResearchAnchorAuditTests(unittest.TestCase):
    def fixture(self,root):
        start=date(2026,7,1)
        days=[]
        for i in range(200):
            d=start+timedelta(days=i)
            if d.weekday()<5:days.append(d.isoformat())
        rows=[{"date":d,"close":100+i*.15,"high":100+i*.15+.5,
               "low":100+i*.15-.5,"volume":10000} for i,d in enumerate(days)]
        signal=rows[80]
        first=rows[41]
        pivot=max(x["high"] for x in rows[41:80])
        anchor={"schema":"vestra_prebreakout_asof_base_anchor_v1",
                "session":signal["date"],"base_start_session":first["date"],
                "reference_bars":39,"window_bars":40,
                "adjusted_close":signal["close"],"adjusted_pivot_high":pivot,
                "observed_last_high":signal["high"],
                "closed_bar_snapshot_sha256":"a"*64,
                "historical_adjustment_factor_verified":False,
                "research_only_no_eligibility_or_score_effect":True}
        observed={"ticker":"AAA","evaluable":True,"last_session":signal["date"],
                  "geometry_shadow":{"research_only_not_eligibility":True,
                      "base_width_pass":True,"contractions_pass":False},
                  "research_prebreakout_lineage":{"unbroken_prebreakout_position":True},
                  "asof_base_price_anchor":anchor}
        day=signal["date"]
        path=root/"2026"/"slots"
        path.mkdir(parents=True)
        data={"schema":"vestra_prebreakout_v1",
              "generated_at":day+"T18:10:00Z","scan_slot_utc":3,
              "signals":[],"research_observations":{
                  "point_in_time_capture_not_historical_reconstruction":True,
                  "rows":[observed]}}
        (path/(day+"-slot3.json")).write_text(json.dumps(data))
        return rows,observed

    def test_snapshot_provenance_and_forward_close_sensitivity(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            rows,obs=self.fixture(folder)
            cases=research_anchor_cases(folder)
            self.assertEqual(len(cases),1)
            self.assertEqual(cases[0]["pivot"],obs["asof_base_price_anchor"]["adjusted_pivot_high"])
            result=research_anchor_forward_audit(folder,{"AAA":rows},rows)
            self.assertEqual(result["selected_bases"],1)
            self.assertTrue(result["research_only"])
            self.assertTrue(result["not_qualified_signal_cohorts"])
            self.assertTrue(result["no_probability_or_ranking_effect"])
            self.assertEqual(result["status_counts"],{"verified_with_matured_forward_observation":1})
            self.assertIsInstance(result["records"][0]["forward_return_pct"]["20"],float)
            self.assertEqual(result["matured_by_horizon"]["5"],1)
            revised=copy.deepcopy(rows)
            revised[73]["high"]+=10
            changed=research_anchor_forward_audit(folder,{"AAA":revised},rows)
            self.assertEqual(changed["status_counts"],{"adjusted_price_basis_changed_or_conflicted":1})
            self.assertIsNone(changed["records"][0]["forward_return_pct"]["5"])

    def test_unavailable_prices_and_missing_context_remain_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            rows,_=self.fixture(folder)
            missing=research_anchor_forward_audit(folder,{},rows)
            self.assertEqual(missing["status_counts"],{"independent_ohlcv_unavailable":1})
            self.assertEqual(missing["matured_by_horizon"]["5"],0)
            # A reference history with a missing prior session cannot be
            # compressed into a fabricated 39-session reference.
            incomplete=research_anchor_forward_audit(folder,{"AAA":rows[:50]+rows[51:]},rows)
            self.assertEqual(incomplete["status_counts"],{"historical_base_window_unverifiable":1})


if __name__=="__main__":
    unittest.main()
