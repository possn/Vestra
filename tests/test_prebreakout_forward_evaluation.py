import importlib.util
from datetime import date,timedelta
from pathlib import Path
import unittest
p=Path(__file__).resolve().parents[1]/"scripts/prebreakout_forward_evaluation.py"
spec=importlib.util.spec_from_file_location("evaluation",p)
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

class EvaluationTests(unittest.TestCase):
 def rows(self,prices):
  origin=date(2026,1,1)
  return [{"date":(origin+timedelta(days=i)).isoformat(),"close":v} for i,v in enumerate(prices)]
 def test_next_common_session_no_lookahead(self):
  a=self.rows([100,101,110,120,130]);b=self.rows([100,100,100,100,100])
  r=mod.evaluate({"ticker":"TEST","date":"2026-01-01"},a,b,horizons=(1,2))
  self.assertEqual(r["entry"],"2026-01-02")
  self.assertAlmostEqual(r["results"][1]["return"],110/101-1)
  self.assertEqual(r["results"][2]["exit"],"2026-01-04")
 def test_insufficient_future_stays_missing(self):
  r=mod.evaluate({"date":"2026-01-02"},self.rows([100,110,120]),self.rows([100,110,120]),horizons=(5,))
  self.assertIsNone(r["results"][5])
 def test_missing_benchmark_is_not_filled(self):
  a=self.rows([100,110,120,130,140])
  b=self.rows([100,110,120,130,140]);b.pop(2)
  r=mod.evaluate({"date":"2026-01-01"},a,b,horizons=(1,))
  self.assertEqual(r["results"][1]["exit"],"2026-01-04")
 def test_duplicate_sessions_rejected(self):
  a=self.rows([100,120]);a.append(a[0])
  with self.assertRaises(ValueError):mod.evaluate({"date":"2026-01-01"},a,self.rows([100,120]))
 def test_max_adverse_excursion_and_summary(self):
  r=mod.evaluate({"date":"2026-01-01"},self.rows([100,100,90,110]),self.rows([100]*4),horizons=(2,))
  self.assertAlmostEqual(r["results"][2]["max_adverse_excursion"],-.1)
  self.assertEqual(mod.aggregate([r],horizons=(2,))[2]["n"],1)
if __name__=="__main__":unittest.main()
