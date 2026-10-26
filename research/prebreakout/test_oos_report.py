import json
import unittest
from datetime import date, timedelta
from oos_report import evaluate_folds, canonical_report_json

CHECKSUM="a"*64
SESSIONS=[(date(2024,1,1)+timedelta(days=i)).isoformat() for i in range(470)]
BOUNDARY={"start_date":"2025-01-01","end_date":"2025-04-01",
          "start_session":SESSIONS.index("2025-01-01")}

def event(issuer, ep, day, end):
    return {"issuer_id":issuer,"episode_id":ep,"signal_date":day,
            "signal_session":SESSIONS.index(day),"label_end_session":SESSIONS.index(end),
            "label_end_date":end}

def trade(e, gross, cost):
    return {"issuer_id":e["issuer_id"],"episode_id":e["episode_id"],
            "signal_date":e["signal_date"],"gross_return_pct":gross,
            "total_cost_pct":cost}

class ReportTests(unittest.TestCase):
    def sample(self):
        events=[event("TRAIN","old","2024-01-20","2024-02-01"),
                event("TEST","new","2025-02-01","2025-02-15")]
        a=[trade(events[0],99,1),trade(events[1],5,1)]
        b=[trade(events[0],0,1),trade(events[1],2,1)]
        return events,a,b

    def test_test_only_and_reproducible(self):
        events,a,b=self.sample()
        args=dict(dataset_sha256=CHECKSUM,reference_sessions=SESSIONS,min_train_issuers=1,
                  min_test_issuers=1,bootstrap_issuers=2,repetitions=250)
        report=evaluate_folds(events,a,b,[BOUNDARY],**args)
        fold=report["folds"][0]
        self.assertEqual(fold["challenger"]["mean_net_pct"],4)
        self.assertEqual(fold["paired_delta"]["mean_delta_net_pct"],3)
        self.assertEqual(fold["issuer_interval"]["status"],"insufficient_clusters")
        self.assertEqual(canonical_report_json(report),
                         canonical_report_json(evaluate_folds(events,a,b,[BOUNDARY],**args)))

    def test_insufficient_fold_abstains(self):
        events,a,b=self.sample()
        r=evaluate_folds(events,a,b,[BOUNDARY],dataset_sha256=CHECKSUM,reference_sessions=SESSIONS)
        self.assertIsNone(r["folds"][0]["paired_delta"])
        self.assertIsNone(r["folds"][0]["challenger"])

    def test_monthly_interval_abstains_with_only_one_period(self):
        events,a,b=self.sample()
        report=evaluate_folds(events,a,b,[BOUNDARY],dataset_sha256=CHECKSUM,
                              min_train_issuers=1,min_test_issuers=1,
                              bootstrap_issuers=2,bootstrap_periods=2,repetitions=250,\n                              reference_sessions=SESSIONS)
        interval=report["folds"][0]["market_period_interval"]
        self.assertEqual(interval["status"],"insufficient_periods_or_issuers")
        self.assertIsNone(interval["ci95_lower_pct"])

    def test_requires_reference_calendar(self):
        events,a,b=self.sample()
        with self.assertRaises(ValueError):
            evaluate_folds(events,a,b,[BOUNDARY],dataset_sha256=CHECKSUM)

    def test_rejects_calendar_mismatch(self):
        events,a,b=self.sample()
        events[1]["label_end_session"] += 1
        with self.assertRaises(ValueError):
            evaluate_folds(events,a,b,[BOUNDARY],dataset_sha256=CHECKSUM,
                           reference_sessions=SESSIONS)

    def test_missing_pair_fails(self):
        events,a,b=self.sample()
        with self.assertRaises(ValueError):
            evaluate_folds(events,a,b[:-1],[BOUNDARY],dataset_sha256=CHECKSUM)

    def test_misaligned_pair_fails(self):
        events,a,b=self.sample()
        b[1]["episode_id"]="other"
        with self.assertRaises(ValueError):
            evaluate_folds(events,a,b,[BOUNDARY],dataset_sha256=CHECKSUM)

    def test_invalid_checksum_fails(self):
        events,a,b=self.sample()
        with self.assertRaises(ValueError):
            evaluate_folds(events,a,b,[BOUNDARY],dataset_sha256="not-a-checksum",reference_sessions=SESSIONS)

if __name__=="__main__":
    unittest.main()
