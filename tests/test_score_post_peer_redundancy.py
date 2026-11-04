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

    def test_bank_factor_diagnostics_before_model_revision(self):
        # Diagnostic-only test: print raw factor dependencies and coverage.
        # A high dimension correlation does not alone identify duplicated inputs.
        payload = json.loads((ROOT / "data" / "stocks.json").read_text(encoding="utf-8"))
        raw = [r for r in (payload.get("stocks") or [])
               if isinstance(r, dict) and r.get("score_model") == "bank"]
        fields = ("roe", "roa", "profit_margin", "efficiency_ratio_proxy",
                  "equity_to_assets", "net_interest_income_yoy")
        print(f"BANK FACTOR DIAGNOSTIC: raw rows={len(raw)}, shadow rows={len(self.by_model['bank'])}")
        for field in fields:
            vals = [score_audit.num(r.get(field)) for r in raw]
            vals = [v for v in vals if v is not None]
            print(f"BANK factor={field}, observed={len(vals)}, unique={len(set(vals))}, min={min(vals) if vals else None}, max={max(vals) if vals else None}")
        for left, right in (("roe", "efficiency_ratio_proxy"),
                            ("roa", "efficiency_ratio_proxy"),
                            ("profit_margin", "efficiency_ratio_proxy"),
                            ("roe", "roa"), ("roe", "profit_margin"),
                            ("roa", "profit_margin")):
            pairs = [(score_audit.num(r.get(left)), score_audit.num(r.get(right))) for r in raw]
            present = [(a,b) for a,b in pairs if a is not None and b is not None]
            rho = score_audit.spearman_pairs(present)
            print(f"BANK raw {left} <> {right}: N={len(present)}, spearman={rho}")
        shadow = self.by_model["bank"]
        for left, right in (("Bank Quality", "Efficiency"), ("Bank Quality", "Capital Proxy")):
            pairs = [((r.get("shadow_dimensions") or {}).get(left),
                      (r.get("shadow_dimensions") or {}).get(right)) for r in shadow]
            present = [(a,b) for a,b in pairs if score_audit.num(a) is not None and score_audit.num(b) is not None]
            rho = score_audit.spearman_pairs(present)
            print(f"BANK shadow {left} <> {right}: N={len(present)}, Spearman={rho}")

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
