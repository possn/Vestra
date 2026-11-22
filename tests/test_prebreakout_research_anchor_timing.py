"""Causal time and complete-session guarantees for archived research anchors."""
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_prebreakout_forward_cohorts import research_anchor_forward_audit

class AnchorForwardTimingTests(unittest.TestCase):
    def sample(self):
        days=[]
        current=date(2026, 8, 3)
        while len(days)<90:
            if current.weekday()<5:
                days.append(current.isoformat())
            current+=timedelta(days=1)
        closes=[100.0 if i<=40 else 100.0+float(i-40) for i in range(len(days))]
        bars=[{"date":day,"close":closes[i],
               "high":max(110.0,closes[i]),"low":90.0,"volume":100000}
              for i,day in enumerate(days)]
        # The as-of bar is idx 40, publication later at idx 44.
        case={"ticker":"A","session":days[40],"base_start_session":days[1],
              "published_at":days[44]+"T22:40:00+00:00",
              "close":100.0,"pivot":110.0,"fingerprint":"abc"}
        spy=[{"date":d,"close":100.0} for d in days]
        return case,bars,spy,days,closes

    def test_no_forward_price_preceding_actual_publication(self):
        case,bars,spy,days,closes=self.sample()
        with patch("build_prebreakout_forward_cohorts.research_anchor_cases",
                   return_value=[case]):
            out=research_anchor_forward_audit(Path("/does/not/matter"),
                                              {"A":bars},spy)
        row=out["records"][0]
        self.assertEqual(row["entry_session"],days[45])
        self.assertEqual(row["status"],"verified_with_matured_forward_observation")
        expected=round((closes[50]/closes[45]-1)*100,4)
        self.assertEqual(row["forward_return_pct"]["5"],expected)
        # An illegal earlier entry from the signal bar has a different return.
        self.assertNotEqual(expected,round((closes[45]/closes[41]-1)*100,4))

    def test_missing_intermediate_asset_session_abstains(self):
        case,bars,spy,days,_=self.sample()
        bars=[bar for bar in bars if bar["date"]!=days[48]]
        with patch("build_prebreakout_forward_cohorts.research_anchor_cases",
                   return_value=[case]):
            out=research_anchor_forward_audit(Path("/does/not/matter"),
                                              {"A":bars},spy)
        row=out["records"][0]
        self.assertEqual(row["status"],"forward_sessions_missing")
        self.assertIsNone(row["forward_return_pct"]["5"])
        self.assertIsNone(row["forward_return_pct"]["10"])
        self.assertEqual(row["entry_session"],days[45])

    def test_no_sessions_matured_remains_pending(self):
        case,bars,spy,days,_=self.sample()
        # Only two forward benchmark sessions have elapsed since publication.
        limited=[row for row in spy if row["date"]<=days[46]]
        with patch("build_prebreakout_forward_cohorts.research_anchor_cases",
                   return_value=[case]):
            out=research_anchor_forward_audit(Path("/does/not/matter"),
                                              {"A":bars},limited)
        self.assertEqual(out["records"][0]["status"],"verified_pending")
        self.assertIsNone(out["records"][0]["forward_return_pct"]["5"])

if __name__=="__main__":
    unittest.main()
