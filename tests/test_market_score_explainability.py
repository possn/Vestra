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

    def test_score_layers_are_explicit(self):
        self.assertIn('1 · Ranking fundamental.', self.market)
        self.assertIn('2 · Qualidade da evidência.', self.market)
        self.assertIn('3 · Travão de risco.', self.market)
        self.assertIn('4 · Valuation, tese e expectativas.', self.market)
        self.assertIn('5 · Decisão de carteira.', self.market)
        self.assertIn('scoreModelWeights', self.market)

    def test_public_score_moderation_is_explained(self):
        self.assertIn('score_raw', self.market)
        self.assertIn('critical_metric_coverage_pct', self.market)
        self.assertIn('score_reliability', self.market)
        self.assertIn('score_cap', self.market)
        self.assertIn('Risk Gate', self.market)

    def test_specialist_model_weights_are_visible(self):
        for token in ('growth_tech', 'bank', 'reit', 'insurance', 'utility', 'energy', 'biotech'):
            self.assertIn(token, self.market)
        self.assertIn("['Cash runway',25]", self.market)
        self.assertIn("['Qualidade bancária',22]", self.market)

if __name__ == '__main__':
    unittest.main(verbosity=2)
