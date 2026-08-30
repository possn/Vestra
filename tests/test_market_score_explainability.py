from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class MarketScoreExplainabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.market=(ROOT/'market.js').read_text(encoding='utf-8')

    def test_score_is_explicitly_not_return_forecast(self):
        self.assertIn('não é uma previsão de retorno', self.market)
        self.assertIn('percentil 80', self.market)

    def test_strengths_and_weaknesses_are_explained(self):
        self.assertIn('A puxar para cima:', self.market)
        self.assertIn('A limitar a avaliação:', self.market)
        self.assertIn('sort((a,b)=>b.value-a.value)', self.market)

    def test_coverage_model_and_missing_data_are_visible(self):
        self.assertIn('scoreModelLabel', self.market)
        self.assertIn('Cobertura ${coverage', self.market)
        self.assertIn('Os pesos dos pilares disponíveis são renormalizados', self.market)

    def test_overview_renders_explanation(self):
        self.assertIn('${scoreExplanation(s)}<details', self.market)
        self.assertIn('Pilares · percentis relativos', self.market)

if __name__ == '__main__':
    unittest.main(verbosity=2)
