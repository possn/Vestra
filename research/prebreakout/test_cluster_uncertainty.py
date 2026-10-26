import unittest
from cluster_uncertainty import issuer_cluster_bootstrap


def row(issuer, episode, value):
    return {"issuer_id":issuer, "episode_id":episode,
            "signal_date":"2025-01-02", "delta_net_pct":value}


class ClusterUncertaintyTests(unittest.TestCase):
    def test_small_issuer_sample_abstains(self):
        result=issuer_cluster_bootstrap([row("A","e1",2),row("A","e2",-1)])
        self.assertEqual(result["status"],"insufficient_clusters")
        self.assertIsNone(result["ci95_lower_pct"])

    def test_constant_clusters_have_exact_zero_width_interval(self):
        rows=[row(f"I{i}","e1",3) for i in range(30)]
        result=issuer_cluster_bootstrap(rows,repetitions=250)
        self.assertEqual(result["mean_delta_net_pct"],3)
        self.assertEqual(result["ci95_lower_pct"],3)
        self.assertEqual(result["ci95_upper_pct"],3)

    def test_deterministic_and_cluster_weighted(self):
        rows=[row("A","e1",1),row("A","e2",1),row("B","e1",5),
              row("C","e1",-2)]
        a=issuer_cluster_bootstrap(rows,repetitions=250,minimum_issuers=3)
        b=issuer_cluster_bootstrap(rows,repetitions=250,minimum_issuers=3)
        self.assertEqual(a,b)
        self.assertAlmostEqual(a["mean_delta_net_pct"],1.25)

    def test_duplicate_episode_refused(self):
        with self.assertRaises(ValueError):
            issuer_cluster_bootstrap([row("A","e1",1),row("A","e1",2)])

    def test_nonfinite_refused(self):
        with self.assertRaises(ValueError):
            issuer_cluster_bootstrap([row("A","e1",float("nan"))])


if __name__=="__main__":
    unittest.main()
