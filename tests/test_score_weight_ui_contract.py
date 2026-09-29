from pathlib import Path
import ast
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ScoreWeightContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.score = (ROOT / "scripts" / "score.py").read_text(encoding="utf-8")
        cls.audit = (ROOT / "scripts" / "score_audit.py").read_text(encoding="utf-8")
        cls.shadow = (ROOT / "scripts" / "score_peer_shadow.py").read_text(encoding="utf-8")
        cls.market = (ROOT / "market.js").read_text(encoding="utf-8")

    def test_production_and_dossier_weight_vectors_match(self):
        expected = {
            "general": [18, 15, 14, 8, 12, 10, 10, 8, 5],
            "growth_tech": [20, 22, 12, 10, 7, 12, 9, 5, 3],
            "bank": [22, 13, 10, 15, 15, 15, 5, 5],
            "reit": [22, 16, 20, 20, 17, 5],
            "insurance": [22, 18, 18, 12, 17, 8, 5],
            "utility": [18, 22, 18, 17, 10, 10, 5],
            "energy": [20, 22, 18, 20, 10, 10],
            "biotech": [25, 15, 20, 20, 10, 10],
        }

        production_tokens = {
            "bank": "composite = _weighted([(bank_quality,.22),(bank_efficiency,.13),(bank_asset_quality,.10),(bank_capital,.15),(bank_growth,.15),(bank_value,.15),(income,.05),(stability,.05)])",
            "reit": "composite = _weighted([(reit_quality,.22),(growth,.16),(reit_leverage,.20),(reit_value,.20),(reit_distribution,.17),(stability,.05)])",
            "insurance": "composite = _weighted([(ins_quality,.22),(ins_underwriting,.18),(ins_capital,.18),(growth,.12),(ins_value,.17),(ins_income_quality,.08),(stability,.05)])",
            "utility": "composite = _weighted([(util_quality,.18),(util_balance,.22),(util_income,.18),(util_value,.17),(growth,.10),(stability,.10),(util_cash,.05)])",
            "energy": "composite = _weighted([(energy_quality,.20),(energy_cash,.22),(energy_balance,.18),(energy_value,.20),(growth,.10),(stability,.10)])",
            "biotech": "composite = _weighted([(runway_score,.25),(biotech_cash,.15),(biotech_dilution,.20),(growth,.20),(biotech_quality,.10),(stability,.10)])",
            "growth_tech": "composite = _weighted([(quality,.20),(growth,.22),(balance,.12),(cashflow,.10),(tech_value,.07),(execution,.12),(earnings_quality,.09),(capital_allocation,.05),(stability,.03)])",
        }
        for model, token in production_tokens.items():
            self.assertIn(token, self.score, f"production weights changed for {model}")

        general_pattern = re.compile(
            r"composite\s*=\s*_weighted\(\[\s*"
            r"\(quality,\.18\),\(growth,\.15\),\(balance,\.14\),\(cashflow,\.08\),\(value,\.12\),\s*"
            r"\(execution,\.10\),\(earnings_quality,\.10\),\(capital_allocation,\.08\),\(stability,\.05\)\s*\]\)"
        )
        self.assertRegex(self.score, general_pattern)

        start = self.market.index("function scoreModelWeights(model)")
        end = self.market.index("\n  function scoreRiskExplanation", start)
        block = self.market[start:end]
        for model, weights in expected.items():
            match = re.search(rf"{model}:\[(.*?)\](?:,|\n)", block, re.S)
            self.assertIsNotNone(match, f"missing dossier weights for {model}")
            ui_weights = [int(x) for x in re.findall(r",\s*(\d+)\]", match.group(1))]
            self.assertEqual(ui_weights, weights, f"dossier weights drifted for {model}")

        tree = ast.parse(self.audit)
        audit_weights = None
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "MODEL_WEIGHTS" for target in node.targets):
                audit_weights = ast.literal_eval(node.value)
                break
        self.assertIsNotNone(audit_weights, "score audit weight pack missing")
        for model, weights in expected.items():
            self.assertIn(model, audit_weights)
            audit_vector = [round(value * 100) for value in audit_weights[model].values()]
            self.assertEqual(audit_vector, weights, f"score audit weights drifted for {model}")

        shadow_tokens = {
            "bank": "score = weighted([\n        (quality, .22), (efficiency, .13), (asset_quality, .10), (capital, .15),\n        (growth, .15), (value, .15), (income, .05), (stability, .05),\n    ])",
            "reit": "score = weighted([\n        (quality, .22), (growth, .16), (leverage, .20),\n        (value, .20), (distribution, .17), (stability, .05),\n    ])",
            "insurance": "score = weighted([\n        (quality, .22), (underwriting, .18), (capital, .18), (growth, .12),\n        (value, .17), (income, .08), (stability, .05),\n    ])",
            "utility": "score = weighted([\n        (quality, .18), (balance, .22), (income, .18), (value, .17),\n        (growth, .10), (stability, .10), (cashflow, .05),\n    ])",
            "energy": "score = weighted([\n        (quality, .20), (cashflow, .22), (balance, .18), (value, .20),\n        (growth, .10), (stability, .10),\n    ])",
            "biotech": "score = weighted([\n        (runway_score, .25), (net_cash, .15), (dilution, .20),\n        (growth, .20), (quality, .10), (stability, .10),\n    ])",
            "growth_tech": "score = weighted([\n        (quality, .20), (growth, .22), (balance, .12), (cashflow, .10),\n        (value, .07), (execution, .12), (earnings_quality, .09),\n        (capital_allocation, .05), (stability, .03),\n    ])",
        }
        for model, token in shadow_tokens.items():
            self.assertIn(token, self.shadow, f"peer shadow weights drifted for {model}")
        self.assertIn("weights\": \"identical to the production specialist pack", self.shadow)

    def test_dossier_explains_weights_as_base_weights(self):
        self.assertIn("Os pesos-base do modelo", self.market)
        self.assertIn("Quando falta um pilar, ele não vale zero", self.market)
        self.assertIn("Os pesos dos pilares disponíveis são renormalizados", self.market)


if __name__ == "__main__":
    unittest.main(verbosity=2)
