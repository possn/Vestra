"""Prospective small-cap watch snapshots are frozen, not retrospective signals."""
import unittest
from datetime import datetime, timedelta, timezone

from research.prebreakout.smallcap_watch_forward import reconcile


class SmallcapWatchForwardTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,9,2,17,tzinfo=timezone.utc)
        self.start=datetime(2026,8,1,tzinfo=timezone.utc)
        self.days=[(self.start+timedelta(days=i)).date().isoformat() for i in range(80)]
        self.history=[[d,100+i] for i,d in enumerate(self.days)]
        self.spy={d:200+i for i,d in enumerate(self.days)}

    def anchor(self,day):
        return {"geometry_watch_observations":[{"ticker":"ABC", "last_session":day,
                 "status":"partial_geometry_observation_not_signal",
                 "base_width_pass":True,"contractions_pass":False,
                 "technical_evidence":{"return20_pct":2}}]}

    def test_new_anchor_has_no_future_outcomes_even_if_historical_fixture_contains_them(self):
        day=self.days[30]
        out=reconcile({},self.anchor(day),{"ABC":self.history[:31]},
                      dict((d,self.spy[d]) for d in self.days[:31]),self.now)
        self.assertEqual(len(out["prospective_watch_episodes"]),1)
        episode=out["prospective_watch_episodes"][0]
        self.assertEqual(episode["anchor_session"],day)
        self.assertEqual(episode["outcomes"],{})
        self.assertTrue(episode["research_only_not_signal"])

    def test_outcomes_mature_only_after_exact_aligned_session_count(self):
        day=self.days[30]
        initial=reconcile({},self.anchor(day),{"ABC":self.history[:31]},
                          self.spy,self.now)
        previous={"prospective_watch_episodes":initial["prospective_watch_episodes"]}
        later=reconcile(previous,{"geometry_watch_observations":[]},
                        {"ABC":self.history[:36]},self.spy,self.now+timedelta(days=6))
        episode=later["prospective_watch_episodes"][0]
        self.assertEqual(list(episode["outcomes"]),["5"])
        self.assertEqual(episode["outcomes"]["5"]["last_session"],self.days[35])
        self.assertEqual(later["prospective_watch_audit"]["matured_by_horizon"]["5"],1)
        self.assertEqual(later["prospective_watch_audit"]["pending_by_horizon"]["10"],1)
        self.assertIsNone(episode.get("success_probability"))

    def test_missing_benchmark_session_does_not_impute_zero(self):
        day=self.days[30]
        first=reconcile({},self.anchor(day),{"ABC":self.history[:31]},self.spy,self.now)
        spy={k:v for k,v in self.spy.items() if k!=self.days[34]}
        out=reconcile({"prospective_watch_episodes":first["prospective_watch_episodes"]},
                      {"geometry_watch_observations":[]},{"ABC":self.history[:36]},
                      spy,self.now+timedelta(days=6))
        self.assertEqual(out["prospective_watch_episodes"][0]["outcomes"],{})

    def test_revised_adjusted_anchor_is_not_comparable(self):
        day=self.days[30]
        first=reconcile({},self.anchor(day),{"ABC":self.history[:31]},self.spy,self.now)
        changed=[list(x) for x in self.history[:36]]
        changed[30][1]*=0.9
        out=reconcile({"prospective_watch_episodes":first["prospective_watch_episodes"]},
                      {"geometry_watch_observations":[]},{"ABC":changed},self.spy,
                      self.now+timedelta(days=6))
        self.assertEqual(out["prospective_watch_episodes"][0]["outcomes"],{})

    def test_duplicate_slot_does_not_create_new_episode(self):
        day=self.days[30]
        first=reconcile({},self.anchor(day),{"ABC":self.history[:31]},self.spy,self.now)
        next_one=reconcile({"prospective_watch_episodes":first["prospective_watch_episodes"]},
                           self.anchor(day),{"ABC":self.history[:31]},self.spy,
                           self.now+timedelta(hours=4))
        self.assertEqual(len(next_one["prospective_watch_episodes"]),1)


if __name__=="__main__":unittest.main()
