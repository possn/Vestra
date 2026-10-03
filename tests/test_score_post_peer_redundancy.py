import json
import sys
import unittest
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import score_audit
import score_peer_shadow


class ScorePostPeerRedundancyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        payload = json.loads((ROOT / "data" / "stocks.json").read_text(encoding="utf-8"))
        rows = [r for r in (payload.get("stocks") or []) if isinstance(r, dict)]
        _, shadow_rows, _ = score_peer_shadow.build_shadow(rows)
        cls.growth_tech = [r for r in shadow_rows if r.get("score_model") == "growth_tech"]

    def test_growth_tech_shadow_has_enough_rows_for_redundancy_diagnostic(self):
        self.assertGreaterEqual(len(self.growth_tech), 40)

    def test_growth_tech_shadow_dimensions_do_not_cross_redundancy_threshold(self):
        dims = sorted({
            name
            for row in self.growth_tech
            for name in (row.get("shadow_dimensions") or {})
        })
        failures = []
        diagnostics = []
        for left, right in combinations(dims, 2):
            pairs = [
                ((row.get("shadow_dimensions") or {}).get(left),
                 (row.get("shadow_dimensions") or {}).get(right))
                for row in self.growth_tech
            ]
            rho = score_audit.spearman_pairs(pairs)
            if rho is None:
                continue
            diagnostics.append((abs(rho), left, right, rho))
            if abs(rho) >= 0.75:
                failures.append((left, right, round(rho, 4)))

        diagnostics.sort(reverse=True)
        print("growth-tech peer-shadow strongest dimension correlations:")
        for _, left, right, rho in diagnostics[:10]:
            print(f"  {left} <> {right}: spearman={rho:.4f}")

        self.assertEqual(
            failures,
            [],
            "post-peer Growth Tech still has redundant dimensions: " + repr(failures),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
