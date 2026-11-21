#!/usr/bin/env python3
"""Smoke and leakage-contract checks for the research-only turning evaluator."""
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from market_turning_walkforward import evaluate, fit, predict, FEATURES

class TurningWalkforwardTests(unittest.TestCase):
    def test_constant_class_refuses_probability_model(self):
        train=[{"features":{k:1. for k in FEATURES},"label":0} for _ in range(100)]
        self.assertIsNone(fit(train,FEATURES))

    def test_train_only_standardization(self):
        train=[]
        for i in range(100):
            train.append({"features":{k:float(i%20) for k in FEATURES},"label":int(i%20>10)})
        model=fit(train,FEATURES)
        self.assertIsNotNone(model)
        self.assertGreater(predict(model,{k:19. for k in FEATURES},FEATURES),
                           predict(model,{k:0. for k in FEATURES},FEATURES))

    def test_inadequate_history_fails_closed(self):
        base=date(2020,1,1)
        raw={"SPY":[{"date":(base+timedelta(days=i)).isoformat(),
                      "close":100.0+i*.01} for i in range(200)]}
        self.assertFalse(evaluate(raw)["evaluated"])

if __name__=="__main__":
    unittest.main()
