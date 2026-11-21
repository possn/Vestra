"""Contracts for stress-conditioned and matched market-turning research."""
from datetime import date,timedelta
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from market_turning_conditional_ablations import (
    conditional_evaluate,eligible_spy_sessions,variants,KEYS,GROUPS,HORIZON,year_block_brier_skill_ci
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
