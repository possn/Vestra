import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from market_turning_protocol_targets import outcome, evaluate_protocol

class ProtocolTargets(unittest.TestCase):
    def test_tactical_target_before_stop(self):
        self.assertTrue(outcome([120.]*125+[100.,106.,90.]+[100.]*18,125,"tactical_rebound"))
    def test_stop_before_target(self):
        self.assertFalse(outcome([120.]*125+[100.,96.,110.]+[100.]*18,125,"tactical_rebound"))
    def test_cyclical_requires_full_window(self):
        self.assertFalse(outcome([120.]*125+[100.,109.]+[100.]*58+[96.],125,"cyclical_bottom"))
        self.assertTrue(outcome([120.]*125+[100.,109.]+[100.]*59,125,"cyclical_bottom"))
    def test_immature_and_ineligible(self):
        self.assertIsNone(outcome([120.]*125+[100.,110.],125,"tactical_rebound"))
        self.assertIsNone(outcome([100.]*150,125,"tactical_rebound"))
    def test_empty_report_is_not_probability(self):
        report=evaluate_protocol({})
        self.assertFalse(report["live_probability_authorized"])
        self.assertIsNone(report["targets"]["cyclical_bottom"]["model"])
        for target in report["targets"].values():
            experiment = target["vvix_incremental_experiment"]
            self.assertEqual(experiment["complete_samples"], 0)
            self.assertIsNone(experiment["augmented"])
            self.assertFalse(experiment["live_vote_authorized"])

if __name__ == "__main__":
    unittest.main()
