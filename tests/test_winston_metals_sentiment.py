from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "market-metals.js").read_text(encoding="utf-8")
CSS = (ROOT / "market-metals.css").read_text(encoding="utf-8")
LOADER = (ROOT / "market-static-universe.js").read_text(encoding="utf-8")


class WinstonMetalsSentimentTests(unittest.TestCase):
    def test_metals_runtime_rolls_forward(self):
        self.assertIn("Vestra Metals v1.2", JS)
        self.assertIn("window.VestraMetals=Object.freeze({version:'1.2'", JS)
        self.assertIn("market-metals.js?v=1.1", LOADER)
        self.assertIn("market-metals.css?v=1.1", JS)

    def test_sentiment_is_transparent_and_price_derived(self):
        self.assertIn("function sentimentFor(detail,quote)", JS)
        self.assertIn("Tendência curta", JS)
        self.assertIn("Momentum 1m", JS)
        self.assertIn("Momentum 3m", JS)
        self.assertIn("rangePos", JS)
        self.assertIn("Não é uma recomendação.", JS)

    def test_editorial_gauge_and_explainer_are_present(self):
        self.assertIn("function sentimentGauge(sentiment)", JS)
        self.assertIn("BARÓMETRO DE SENTIMENTO", JS)
        self.assertIn("O QUE ESTÁS A VER.", JS)
        self.assertIn("metal-sentiment-gauge", CSS)
        self.assertIn("metal-explainer", CSS)
        self.assertIn("font-family:Georgia", CSS)
        self.assertNotIn("var(--ink)", CSS)
        self.assertIn("overflow-wrap:anywhere", CSS)
        self.assertIn("@media(max-width:360px)", CSS)

    def test_no_unavailable_positioning_is_claimed(self):
        self.assertIn("não inclui ainda COT", JS)
        self.assertIn("Será enriquecido depois", JS)


if __name__ == "__main__":
    unittest.main(verbosity=2)
