from pathlib import Path
import ast
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ScoreSpecialistPeerBenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / "scripts" / "score.py").read_text(encoding="utf-8")

    def test_peer_benchmark_requires_twenty_finite_observations(self):
        tree = ast.parse(self.source)
        fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_benchmark_values")
        ns = {"MIN_SPECIALIST_PEER_OBSERVATIONS": 20}
        exec(compile(ast.Module(body=[fn], type_ignores=[]), "<benchmark-values>", "exec"), ns)
        benchmark = ns["_benchmark_values"]

        global_values = list(range(100))
        peer_20 = list(range(20))
        peer_19 = list(range(19)) + [None]

        self.assertEqual(benchmark(peer_20, global_values), peer_20)
        self.assertEqual(benchmark(peer_19, global_values), global_values)

    def test_all_specialist_models_use_same_model_peer_sets(self):
        s = self.source
        for model in ("bank", "reit", "insurance", "utility", "energy", "biotech", "growth_tech"):
            self.assertIn(f'peers = peers_by_model["{model}"]', s)

        self.assertIn("bank_growth = _avg([peer_growth_score(r, peers), bank_nii_growth])", s)
        self.assertIn("bank_stability = peer_stability_score(r, peers)", s)

        self.assertIn("reit_growth = peer_growth_score(r, peers)", s)
        self.assertIn("reit_stability = peer_stability_score(r, peers)", s)
        self.assertIn("reit_coverage = _percentile_rank(coverage, peer_interest_coverages(peers))", s)

        self.assertIn("ins_growth = peer_growth_score(r, peers)", s)
        self.assertIn("ins_stability = peer_stability_score(r, peers)", s)

        self.assertIn("util_growth = peer_growth_score(r, peers)", s)
        self.assertIn("util_stability = peer_stability_score(r, peers)", s)
        self.assertIn("util_coverage = _percentile_rank(coverage, peer_interest_coverages(peers))", s)

        self.assertIn("energy_growth = peer_growth_score(r, peers)", s)
        self.assertIn("energy_stability = peer_stability_score(r, peers)", s)
        self.assertIn("energy_coverage = _percentile_rank(coverage, peer_interest_coverages(peers))", s)

        self.assertIn("biotech_growth = peer_growth_score(r, peers)", s)
        self.assertIn("biotech_stability = peer_stability_score(r, peers)", s)

    def test_growth_tech_no_longer_inherits_global_core_dimensions(self):
        s = self.source
        block = s.split('elif model == "growth_tech":', 1)[1].split(
            '        else:\n            # Execution is operating momentum', 1
        )[0]
        for token in (
            "tech_quality = _avg([",
            "tech_growth = peer_growth_score(r, peers)",
            "tech_balance = _avg([",
            "tech_cashflow = peer_cashflow_score(r, peers, fcf_yield)",
            "peer_derived_values(peers,cash_conversion)",
            "peer_derived_values(peers,accrual_ratios)",
            "peer_derived_values(peers,fcf_margins)",
            "tech_stability = peer_stability_score(r, peers)",
        ):
            self.assertIn(token, block)
        self.assertNotIn("composite = _weighted([(quality,.20),(growth,.22),(balance,.12),(cashflow,.10)", block)

    def test_general_model_keeps_global_cross_section(self):
        prefix = self.source.split('        if model == "bank":', 1)[0]
        self.assertIn('_percentile_rank(r.roe, arr("roe"))', prefix)
        self.assertIn('_percentile_rank(r.revenue_growth, arr("revenue_growth"))', prefix)
        self.assertIn('_percentile_rank(r.beta, arr("beta"), invert=True)', prefix)

    def test_specialist_model_note_explains_peer_first_fallback(self):
        self.assertIn(
            'Percentiles use same-model peers when at least 20 finite observations exist; sparse metrics fall back to the full equity universe.',
            self.source,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
