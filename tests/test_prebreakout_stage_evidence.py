import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from prebreakout_stage_evidence import report,wilson

class StageEvidenceTests(unittest.TestCase):
    def sample(self,stage,ret=0.1):
        return {"stage":stage,"results":{5:{"return":ret,"excess_return":ret-.02,
            "max_adverse_excursion":-.05}}}

    def test_small_sample_never_advertises_hit_rate(self):
        result=report([self.sample("pré-breakout")],horizons=(5,10))
        five=result["stages"]["pré-breakout"]["5"]
        self.assertEqual(five["n"],1)
        self.assertEqual(five["coverage"],1)
        self.assertFalse(five["sufficient_sample"])
        self.assertNotIn("hit_rate",five)
        self.assertNotIn("benchmark_outperformance_rate",five)
        self.assertEqual(result["stages"]["pré-breakout"]["10"]["n_missing"],1)

    def test_wilson_and_stage_separation(self):
        values=[self.sample("confirmado",.1)]*24+[self.sample("confirmado",-.1)]*6
        values.append(self.sample("compressão"))
        result=report(values,horizons=(5,))
        confirmed=result["stages"]["confirmado"]["5"]
        self.assertAlmostEqual(confirmed["hit_rate"],.8)
        self.assertAlmostEqual(confirmed["benchmark_outperformance_rate"],.8)
        lower,upper=confirmed["benchmark_outperformance_wilson_95"]
        self.assertTrue(0<lower<.8<upper<1)
        self.assertEqual(confirmed["n"],30)
        self.assertEqual(confirmed["n_observations"],30)
        lo,hi=confirmed["hit_rate_wilson_95"]
        self.assertTrue(0<lo<.8<hi<1)
        self.assertNotIn("hit_rate",result["stages"]["compressão"]["5"])

    def test_missing_and_nonfinite_not_counted(self):
        values=[self.sample("compressão") for _ in range(31)]
        values[-1]["results"][5]["return"]=float("nan")
        result=report(values,horizons=(5,))
        row=result["stages"]["compressão"]["5"]
        self.assertEqual(row["n"],30)
        self.assertEqual(row["n_missing"],1)
        self.assertAlmostEqual(row["coverage"],30/31)

    def test_invalid_wilson_rejected(self):
        with self.assertRaises(ValueError):wilson(1,0)
        with self.assertRaises(ValueError):wilson(3,2)

if __name__=="__main__":
    unittest.main()
