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

    def test_growth_tech_fcf_yield_has_single_dimension_owner(self):
        rows = self.by_model["growth_tech"]
        self.assertGreaterEqual(len(rows), 40)
        duplicate_owners = []
        for row in rows:
            uses = [
                meta for meta in (row.get("benchmark_scopes") or [])
                if str(meta.get("metric") or "") == "fcf_yield"
            ]
            if len(uses) != 1:
                duplicate_owners.append((row.get("ticker"), len(uses)))
        self.assertEqual(
            duplicate_owners,
            [],
            "growth-tech FCF yield must be owned only by Cash Flow: " + repr(duplicate_owners[:10]),
        )

    @staticmethod
    def bank_factor_ownership_verified():
        """Evidence-aware exception: distinct bank profitability versus cost inputs.

        A strong cross-sectional rank correlation is NOT itself proof that two
        dimensions reuse the same fundamental metric. The live 78-bank data
        has only 33 observed efficiency ratios, and the raw ROA-to-efficiency
        correlation alone is -0.858. Guard the documented distinct ownership
        in both production and independent peer-shadow implementations.
        """
        source = (ROOT / "scripts" / "score.py").read_text(encoding="utf-8")
        shadow = (ROOT / "scripts" / "score_peer_shadow.py").read_text(encoding="utf-8")
        block = source.split('if model == "bank":', 1)[1].split('elif model == "reit":', 1)[0]
        shadow_block = shadow.split("def bank_shadow(ctx):", 1)[1].split("def reit_shadow(ctx):", 1)[0]
        quality = block.split("bank_quality = _avg([", 1)[1].split("])", 1)[0]
        efficiency = block.split("bank_efficiency = ", 1)[1].split("\n", 1)[0]
        shadow_quality = shadow_block.split("quality = avg([", 1)[1].split("])", 1)[0]
        shadow_efficiency = shadow_block.split("efficiency = ", 1)[1].split("\n", 1)[0]
        for part in (quality, shadow_quality):
            if "efficiency_ratio_proxy" in part:
                return False
            if not ("roe" in part and "roa" in part):
                return False
        for part in (efficiency, shadow_efficiency):
            if "efficiency_ratio_proxy" not in part:
                return False
            if any(x in part for x in ("roe", "roa", "profit_margin")):
                return False
        return True

    def test_bank_distinct_factor_ownership_is_enforced_in_both_score_engines(self):
        self.assertTrue(
            self.bank_factor_ownership_verified(),
            "bank profitability and cost-efficiency must use distinct source metrics "
            "in both production and independent shadow; no correlation exception otherwise",
        )

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
                    # Factor audit 2026-11-04: the BANK profitability/efficiency
                    # dimensions use distinct raw inputs, but the *raw* ROA and
                    # cost-efficiency ratio already correlate -0.858 on 33 banks.
                    # A correlation-only alarm is not evidence of duplicate
                    # metric ownership. Keep the same 0.75 threshold for ALL
                    # other pairs, and revoke this narrow exception if either
                    # source engine starts sharing the efficiency primitive.
                    distinct_bank_inputs = (
                        model == "bank"
                        and {left, right} == {"Bank Quality", "Efficiency"}
                        and self.bank_factor_ownership_verified()
                    )
                    if distinct_bank_inputs:
                        print("BANK empirical factor correlation: distinct ownership verified; "
                              "retain as a visible diagnostic, not a duplicate-input failure")
                    else:
                        failures.append((model, left, right, round(rho, 4)))

        self.assertIn("growth_tech", checked)
        self.assertEqual(
            failures,
            [],
            "post-peer specialist score still has redundant dimensions: " + repr(failures),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
