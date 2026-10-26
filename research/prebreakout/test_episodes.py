import unittest
from episodes import group_episodes

def row(issuer, ordinal, day="2025-01-01"):
    return {"issuer_id":issuer,"session_ordinal":ordinal,"signal_date":day}

class EpisodeTests(unittest.TestCase):
    def test_repeated_snapshots_are_one_episode(self):
        x=group_episodes([row("A",1),row("A",4),row("A",17)])
        self.assertEqual(len(x),1)
        self.assertEqual(x[0]["observation_count"],3)
    def test_new_episode_after_cooldown(self):
        x=group_episodes([row("A",1),row("A",22)])
        self.assertEqual(len(x),2)
    def test_distinct_issuers(self):
        self.assertEqual(len(group_episodes([row("A",1),row("B",1)])),2)
    def test_duplicate_observations_fail_closed(self):
        with self.assertRaises(ValueError):
            group_episodes([row("A",1),row("A",1)])
    def test_invalid_ordinal_fails(self):
        with self.assertRaises(ValueError):
            group_episodes([row("A",-1)])
if __name__=="__main__":
    unittest.main()
