import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CompanyDossierRadarContractTests(unittest.TestCase):
    def test_radar_is_native_explainable_and_not_a_new_score(self):
        source = (ROOT / "market.js").read_text(encoding="utf-8")
        self.assertIn("function dossierRadarChart(s)", source)
        self.assertIn("function dossierRadarAxes(s)", source)
        self.assertIn("PERFIL VESTRA · 5 EIXOS", source)
        for label in ("Valor", "Futuro", "Histórico", "Saúde", "Dividendo"):
            self.assertIn("label:'%s'" % label, source)
        self.assertIn("Não cria um novo Score nem altera Conviction ou Risk Gate.", source)
        self.assertIn("Empresas sem dividendo não são penalizadas.", source)
        self.assertIn("${dossierRadarChart(s)}", source)
        radar = source[source.index("function dossierRadarChart(s)"):source.index("function smartMoneyEventType")]
        self.assertNotIn("new Chart(", radar)

    def test_radar_keeps_missing_data_semantics_explicit(self):
        source = (ROOT / "market.js").read_text(encoding="utf-8")
        radar = source[source.index("function dossierRadarBlend"):source.index("function smartMoneyEventType")]
        self.assertIn("value==null?50:value", radar)
        self.assertIn("return observed&&weight>0", radar)
        self.assertIn("if(rawYield==null||rawYield<=0) return null", radar)
        self.assertIn("axis.value==null?'N/A'", radar)

    def test_radar_css_is_responsive(self):
        css = (ROOT / "market.css").read_text(encoding="utf-8")
        self.assertIn(".market-dossier-radar{display:grid", css)
        self.assertIn(".market-dossier-radar-area", css)
        self.assertIn("@media(max-width:720px){.market-dossier-radar", css)


if __name__ == "__main__":
    unittest.main(verbosity=2)
