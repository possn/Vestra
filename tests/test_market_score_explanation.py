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

if __name__ == "__main__":
    unittest.main(verbosity=2)
