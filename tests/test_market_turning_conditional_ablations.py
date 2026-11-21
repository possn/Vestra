"""Contracts for stress-conditioned and matched market-turning research."""
from datetime import date,timedelta
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from market_turning_conditional_ablations import (
    conditional_evaluate,eligible_spy_sessions,variants,KEYS,GROUPS,HORIZON
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
