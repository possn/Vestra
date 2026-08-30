from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "market-model-validation.js"
BOOTSTRAP = ROOT / "market-company-brief.js"


class MarketModelValidationTests(unittest.TestCase):
    def test_module_is_valid_javascript(self):
        subprocess.run(["node", "--check", str(MODULE)], check=True, cwd=ROOT)

    def test_canonical_market_bootstrap_loads_validation_once(self):
        text = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn("market-model-validation.js?v=1.0", text)
        self.assertIn("vestra-model-validation-script", text)
        self.assertIn("loadResearchDiagnostics()", text)

    def test_panel_reads_only_canonical_prospective_report(self):
        text = MODULE.read_text(encoding="utf-8")
        self.assertIn("./data/score_validation_report.json", text)
        self.assertIn("cache: 'no-store'", text)
        self.assertNotIn("method: 'POST'", text)
        self.assertNotIn("localStorage", text)
        self.assertNotIn("sessionStorage", text)

    def test_panel_exposes_maturity_not_false_prediction(self):
        text = MODULE.read_text(encoding="utf-8")
        for token in (
            "A recolher dados",
            "Sinal inicial",
            "Evidência múltipla",
            "Rank IC mediano",
            "Top − Bottom",
            "Não é uma previsão de retorno",
        ):
            self.assertIn(token, text)
        self.assertIn("cohort_count", text)
        self.assertIn("median_cohort_rank_ic", text)
        self.assertIn("median_cohort_top_minus_bottom_pct", text)

    def test_schema_v1_remains_a_safe_read_fallback(self):
        text = MODULE.read_text(encoding="utf-8")
        self.assertIn("data.median_cohort_rank_ic ?? data.rank_information_coefficient", text)
        self.assertIn("data.median_cohort_top_minus_bottom_pct ?? data.top_minus_bottom_pct", text)

    def test_missing_validation_numbers_never_become_zero(self):
        text = MODULE.read_text(encoding="utf-8")
        self.assertIn("value === null || value === undefined || value === ''", text)
        self.assertIn("expected_matured_cohorts", text)
        self.assertIn("cohort_capture_pct", text)
        self.assertIn("Cohorts maturados / esperados", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
