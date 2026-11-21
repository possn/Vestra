"""Contracts for stress-conditioned and matched market-turning research."""
from datetime import date,timedelta
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from market_turning_conditional_ablations import (
    conditional_evaluate,eligible_spy_sessions,variants,KEYS,GROUPS,HORIZON,year_block_brier_skill_ci,stress_episode_groups,episode_block_skill_ci,conservative_research_gate
)

class StressConditionedAblationTests(unittest.TestCase):
    def test_short_history_does_not_invent_model(self):
        self.assertEqual(conditional_evaluate({"SPY":[]})["evaluated"],False)

    def test_mutually_exclusive_past_only_conditions(self):
        base=date(2025,1,1)
        rows=[{"date":(base+timedelta(days=i)).isoformat(),"close":100.0}
              for i in range(155)]
        rows[140]["close"]=92.
        bottom=eligible_spy_sessions(rows,"bottom",horizon=10)
        top=eligible_spy_sessions(rows,"top",horizon=10)
        self.assertIn(140,bottom)
        self.assertNotIn(140,top)
        rows[146]["close"]=1.0  # Future candle must not alter past eligibility.
        self.assertIn(140,eligible_spy_sessions(rows,"bottom",horizon=10))
        self.assertNotIn(140,eligible_spy_sessions(rows,"top",horizon=10))

    def test_calendar_block_intervals_are_paired_deterministic_and_research_only(self):
        years=[2015+i//10 for i in range(100)]
        truth=[int(i%9==0) for i in range(100)]
        baseline=[(.14,y) for y in truth]
        model=[(.65 if y else .09,y) for y in truth]
        result=year_block_brier_skill_ci(model,baseline,years,draws=120)
        self.assertTrue(result["available"])
        self.assertEqual(result["calendar_year_blocks"],10)
        self.assertEqual(result["block_unit"],"calendar_year_not_independent_crisis")
        self.assertTrue(result["for_research_only_not_probability_calibration"])
        self.assertEqual(result,year_block_brier_skill_ci(model,baseline,years,draws=120))
        self.assertGreater(result["percentile_95_ci"][0],0)
        with self.assertRaises(ValueError):
            year_block_brier_skill_ci(model,baseline[:-1],years)
        insufficient=year_block_brier_skill_ci(model[:30],baseline[:30],years[:30])
        self.assertFalse(insufficient["available"])

    def test_stress_episodes_preserve_gap_and_reject_noncausal_reordering(self):
        rows=[{"index":x} for x in (125,126,133,160,161,190)]
        groups=stress_episode_groups(rows,max_gap_sessions=20)
        self.assertEqual([groups[x["index"]] for x in rows],[0,0,0,1,1,2])
        with self.assertRaises(ValueError):
            stress_episode_groups([{"index":130},{"index":130}])

    def test_episode_bootstrap_is_paired_deterministic(self):
        ids=[i//12 for i in range(120)]
        actual=[int(i%13==0) for i in range(120)]
        base=[(.15,y) for y in actual]
        model=[(.4 if y else .08,y) for y in actual]
        result=episode_block_skill_ci(model,base,ids,draws=120)
        self.assertTrue(result["available"])
        self.assertEqual(result["stress_episode_blocks"],10)
        self.assertTrue(result["episodes_are_not_proven_independent_market_crises"])
        self.assertEqual(result,episode_block_skill_ci(model,base,ids,draws=120))
        self.assertFalse(episode_block_skill_ci(model[:10],base[:10],ids[:10])["available"])

    def test_historical_strength_cannot_authorize_live_probability(self):
        fake={
            "results":{side:{
                "models":{"full":{"events":100,"n_nonoverlapping_test_anchors":500}},
                "paired_stress_episode_bootstrap":{"full_vs_baseline":{
                    "available":True,"stress_episode_blocks":20,
                    "percentile_95_ci":[.1,.2]}},
                "paired_year_block_bootstrap":{"full_vs_baseline":{
                    "available":True,"percentile_95_ci":[.1,.2]}},
            } for side in ("bottom","top")}
        }
        result=conservative_research_gate(fake)
        self.assertTrue(result["bottom"]["historical_consistency_observed"])
        self.assertFalse(result["bottom"]["live_probability_authorized"])
        self.assertIn("independent_prospective_outcomes_verified",
                      result["bottom"]["promotion_blockers"])
        fake["results"]["bottom"]["paired_stress_episode_bootstrap"]["full_vs_baseline"]["percentile_95_ci"]=[-.01,.2]
        self.assertFalse(conservative_research_gate(fake)["bottom"]["historical_consistency_observed"])

    def test_ablations_preserve_common_complete_case_inputs(self):
        v=variants()
        self.assertEqual(set(v["full"]),set(KEYS))
        self.assertEqual(set(v),{"full",*(("without_"+x) for x in GROUPS)})
        for family,removed in GROUPS.items():
            self.assertEqual(set(v["without_"+family]),set(KEYS)-set(removed))
            self.assertTrue(v["without_"+family])
        self.assertNotIn("drawdown_126_pct",KEYS)

if __name__=="__main__":
    unittest.main()
