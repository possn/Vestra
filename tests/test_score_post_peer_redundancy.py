import json
import sys
import unittest
from collections import defaultdict
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import score_audit
import score_peer_shadow


REDUNDANCY_THRESHOLD = 0.75
MIN_MODEL_ROWS = 20


class ScorePostPeerRedundancyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        payload = json.loads((ROOT / "data" / "stocks.json").read_text(encoding="utf-8"))
        rows = [r for r in (payload.get("stocks") or []) if isinstance(r, dict)]
        _, shadow_rows, _ = score_peer_shadow.build_shadow(rows)
        cls.by_model = defaultdict(list)
        for row in shadow_rows:
            cls.by_model[str(row.get("score_model") or "")].append(row)

    @staticmethod
    def model_diagnostics(rows):
        dims = sorted({
            name
            for row in rows
            for name in (row.get("shadow_dimensions") or {})
        })
        diagnostics = []
        for left, right in combinations(dims, 2):
            pairs = [
                ((row.get("shadow_dimensions") or {}).get(left),
                 (row.get("shadow_dimensions") or {}).get(right))
                for row in rows
            ]
            rho = score_audit.spearman_pairs(pairs)
            if rho is not None:
                diagnostics.append((abs(rho), left, right, rho))
        diagnostics.sort(reverse=True)
        return diagnostics

    def test_growth_tech_shadow_has_enough_rows_for_redundancy_diagnostic(self):
        self.assertGreaterEqual(len(self.by_model["growth_tech"]), 40)

    def test_all_well_sampled_specialist_models_stay_below_redundancy_threshold(self):
        failures = []
        checked = []
        for model in score_peer_shadow.SPECIALIST_MODELS:
            rows = self.by_model.get(model, [])
            if len(rows) < MIN_MODEL_ROWS:
                print(f"{model}: skipped redundancy gate; rows={len(rows)} < {MIN_MODEL_ROWS}")
                continue

            diagnostics = self.model_diagnostics(rows)
            checked.append(model)
            print(f"{model} peer-shadow strongest dimension correlations (rows={len(rows)}):")
            for _, left, right, rho in diagnostics[:10]:
                print(f"  {left} <> {right}: spearman={rho:.4f}")
            for _, left, right, rho in diagnostics:
                if abs(rho) >= REDUNDANCY_THRESHOLD:
                    failures.append((model, left, right, round(rho, 4)))

        self.assertIn("growth_tech", checked)
        self.assertEqual(
            failures,
            [],
            "post-peer specialist score still has redundant dimensions: " + repr(failures),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
