import unittest
from walk_forward import walk_forward_folds

def event(issuer, ep, day, start, end):
    return {"issuer_id":issuer,"episode_id":ep,"signal_date":day,
            "signal_session":start,"label_end_session":end}
FOLD={"start_date":"2025-01-01","end_date":"2025-04-01","start_session":100}

class WalkForwardTests(unittest.TestCase):
    def test_purges_overlapping_labels_and_embargo(self):
        rows=[event("A","1","2024-01-02",45,75),
              event("B","1","2024-11-01",80,85),
              event("C","1","2025-02-02",110,130)]
        out=walk_forward_folds(rows,[FOLD],embargo_sessions=20,
                               min_train_issuers=1,min_test_issuers=1)[0]
        self.assertEqual(out["train_indices"],[0])
        self.assertEqual(out["test_indices"],[2])
        self.assertEqual(out["status"],"eligible_for_offline_evaluation")
    def test_missing_independent_issuers_abstains(self):
        rows=[event("A","1","2025-02-01",101,120)]
        self.assertEqual(walk_forward_folds(rows,[FOLD])[0]["status"],
                         "insufficient_independent_issuers")
    def test_duplicate_episode_fails_closed(self):
        rows=[event("A","1","2024-01-02",45,75)]*2
        with self.assertRaises(ValueError):
            walk_forward_folds(rows,[FOLD])
    def test_bad_calendar_fails_closed(self):
        with self.assertRaises(ValueError):
            walk_forward_folds([event("A","1","2025-02-02",99,110)],[FOLD])
    def test_overlapping_folds_fail_closed(self):
        with self.assertRaises(ValueError):
            walk_forward_folds([], [FOLD,FOLD])
if __name__=="__main__":
    unittest.main()
