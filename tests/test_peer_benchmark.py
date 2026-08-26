import math
import unittest

from scripts.peer_benchmark import peer_first_percentile


class PeerBenchmarkTests(unittest.TestCase):
    def test_uses_peer_model_when_observed_sample_is_deep_enough(self):
        result = peer_first_percentile(5, range(1, 21), range(1, 101), min_peers=20)
        self.assertEqual(result.scope, "peer_model")
        self.assertEqual(result.peer_observations, 20)
        self.assertAlmostEqual(result.score, 25.0)

    def test_falls_back_to_global_when_peer_values_are_sparse(self):
        result = peer_first_percentile(50, [1, 2, None, float("nan")], range(1, 101), min_peers=20)
        self.assertEqual(result.scope, "global_fallback")
        self.assertEqual(result.peer_observations, 2)
        self.assertAlmostEqual(result.score, 50.0)

    def test_missing_value_stays_missing(self):
        result = peer_first_percentile(None, range(20), range(100), min_peers=20)
        self.assertIsNone(result.score)

    def test_inversion_is_preserved(self):
        result = peer_first_percentile(5, range(1, 21), range(1, 101), invert=True, min_peers=20)
        self.assertAlmostEqual(result.score, 75.0)

    def test_non_finite_observations_do_not_count_toward_peer_depth(self):
        peers = list(range(1, 19)) + [None, float("nan"), float("inf")]
        result = peer_first_percentile(10, peers, range(1, 101), min_peers=20)
        self.assertEqual(result.scope, "global_fallback")
        self.assertEqual(result.peer_observations, 18)


if __name__ == "__main__":
    unittest.main(verbosity=2)
