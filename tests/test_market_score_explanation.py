from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
MARKET = ROOT / "market.js"

class MarketScoreExplanationTests(unittest.TestCase):
    def test_market_js_is_valid(self):
        subprocess.run(["node", "--check", str(MARKET)], check=True, cwd=ROOT)

    def test_pillars_expose_raw_metric_evidence(self):
        text = MARKET.read_text(encoding="utf-8")
        for token in (
            "pillarMetricSummary",
            "ROE", "ROA", "Margem operacional",
            "Receitas", "Lucros trimestrais",
            "Current ratio", "Cobertura juros",
            "FCF yield", "Forward P/E", "EV/EBITDA",
            "Conversão caixa/lucro", "Accrual ratio",
            "Diluição YoY", "ROCE proxy", "Beta",
            "métrica em falta",
        ):
            self.assertIn(token, text)

    def test_explanation_does_not_change_score_math(self):
        text = MARKET.read_text(encoding="utf-8")
        self.assertIn("scoreDims(s)", text)
        self.assertNotIn("s.score =", text)
        self.assertNotIn("s.quality_pct =", text)

    def test_specialist_models_use_native_score_dimensions(self):
        text = MARKET.read_text(encoding="utf-8")
        self.assertIn("score_dimensions", text)
        self.assertIn("scoreDimensionLabel", text)
        self.assertIn("Qualidade bancária", text)
        self.assertIn("Qualidade REIT", text)
        self.assertIn("Subscrição", text)
        self.assertIn("Runway de caixa", text)

    def test_model_rationale_is_visible_and_read_only(self):
        text = MARKET.read_text(encoding="utf-8")
        self.assertIn("scoreModelRationale", text)
        self.assertIn("Modelo usado.", text)
        self.assertIn("Bancos: rentabilidade", text)
        self.assertIn("Biotech: runway de caixa", text)
        self.assertNotIn("s.score =", text)

    def test_peer_context_explains_relative_evidence(self):
        text = MARKET.read_text(encoding="utf-8")
        self.assertIn("peerScoreContext", text)
        self.assertIn("Face aos peers", text)
        self.assertIn("forward_pe_vs_sector_pct", text)
        self.assertIn("sector_roe_median", text)
        self.assertIn("sector_operating_margin_median", text)
        self.assertIn("sector_fcf_yield_median", text)
        self.assertIn("Contexto relativo; não é recomendação.", text)
        self.assertNotIn("s.score =", text)

if __name__ == "__main__":
    unittest.main(verbosity=2)
