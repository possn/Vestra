import importlib.util
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("readiness",ROOT/"research/prebreakout/empirical_readiness.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
def fixture():
    return {"schema":"vestra_prebreakout_forward_cohorts_v1",
        "breakout_event_evidence":{"coverage_by_horizon":{
            h:{"cohorts":27,"evaluable":0,"breakout_rate":None,
               "by_status":{"price_basis_unverified":17,"missing_ohlcv":3,"pending":7}}
            for h in ("5","10","20")}}}
class ReadinessTests(unittest.TestCase):
    def test_zero_evaluable_never_fabricates_failure_or_success(self):
        result=mod.audit(fixture())
        self.assertFalse(result["filter_promotion_approved"])
        self.assertTrue(all(v["evaluable"]==0 for v in result["horizons"].values()))
        self.assertIn("NOT failed",mod.markdown(result))
    def test_counts_must_reconcile(self):
        data=fixture();data["breakout_event_evidence"]["coverage_by_horizon"]["5"]["by_status"]["pending"]=6
        with self.assertRaisesRegex(ValueError,"denominators"):mod.audit(data)
    def test_rate_without_verifiable_cases_is_rejected(self):
        data=fixture();data["breakout_event_evidence"]["coverage_by_horizon"]["10"]["breakout_rate"]=0
        with self.assertRaisesRegex(ValueError,"fabricated"):mod.audit(data)
    def test_schema_and_horizons_mandatory(self):
        data=fixture();del data["breakout_event_evidence"]["coverage_by_horizon"]["20"]
        with self.assertRaises(ValueError):mod.audit(data)
if __name__=="__main__":unittest.main()
