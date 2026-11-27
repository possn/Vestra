import unittest
from datetime import datetime, timedelta, timezone
from research.prebreakout.smallcap_accumulation_forward import candidate, reconcile_accumulation

class AccumulationTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,11,27,tzinfo=timezone.utc)
        self.row={"ticker":"ABC","status":"evaluable_ohlcv","currency":"USD",
            "last_session":"2026-11-26","average_dollar_volume_20_usd":2_000_000,
            "technical_evidence_shadow":{"atr14_to_prior46":.7,"normalized_obv_change20":.2,
                "chaikin_money_flow20":.1,"relative_return_20_vs_spy_pct":2},
            "technical_prebreakout_lineage":{"unbroken_prebreakout_position":True,
                "prior_confirmed_breakouts_in_base":0,"distance_to_pivot_pct":5,
                "prebase_impulse_pct":10,"prior_confirmed_breakouts_before_base":0,
                "prebase_volume_lineage_complete":True},
            "technical_base_anchor":{"session":"2026-11-26","adjusted_close":100,
                "adjusted_pivot_high":105,"observed_last_high":104}}
    def test_candidate_requires_all_evidence_and_unbroken_pivot(self):
        self.assertTrue(candidate(self.row,self.now))
        self.row["technical_base_anchor"]["observed_last_high"]=106
        self.assertFalse(candidate(self.row,self.now))
        self.row["technical_base_anchor"]["observed_last_high"]=104
        self.row["technical_evidence_shadow"]["chaikin_money_flow20"]=None
        self.assertFalse(candidate(self.row,self.now))
    def test_previous_breakout_and_unknown_lineage_rejected(self):
        lineage=self.row["technical_prebreakout_lineage"]
        lineage["prior_confirmed_breakouts_before_base"]=1
        self.assertFalse(candidate(self.row,self.now))
        lineage["prior_confirmed_breakouts_before_base"]=0
        lineage["prebase_impulse_pct"]=25
        self.assertFalse(candidate(self.row,self.now))
        lineage["prebase_impulse_pct"]=10
        lineage["prebase_volume_lineage_complete"]=False
        self.assertFalse(candidate(self.row,self.now))
    def test_anchor_frozen_and_later_outcome_observed(self):
        current={"observations":[self.row]}
        history={"ABC":[["2026-11-26",100]]}
        spy={"2026-11-26":200}
        first=reconcile_accumulation({},current,history,spy,self.now)
        self.assertEqual(len(first["accumulation_episodes"]),1)
        self.assertEqual(first["accumulation_episodes"][0]["outcomes"],{})
        duplicate=reconcile_accumulation(first,current,history,spy,self.now+timedelta(hours=4))
        self.assertEqual(len(duplicate["accumulation_episodes"]),1)
        dates=["2026-11-27","2026-11-30","2026-12-01","2026-12-02","2026-12-03"]
        history["ABC"] += [[d,101+i] for i,d in enumerate(dates)]
        spy.update({d:201+i for i,d in enumerate(dates)})
        later=reconcile_accumulation(first,{"observations":[]},history,spy,datetime(2026,12,4,tzinfo=timezone.utc))
        self.assertEqual(later["accumulation_audit"]["matured_by_horizon"]["5"],1)
        self.assertEqual(first["accumulation_episodes"][0]["outcomes"],{})
    def test_no_new_anchor_from_retained_observation(self):
        result=reconcile_accumulation({},{"observations":[self.row]}, {},{"2026-11-26":200},self.now)
        self.assertEqual(result["accumulation_episodes"],[])
