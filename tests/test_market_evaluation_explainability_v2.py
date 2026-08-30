from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class MarketEvaluationExplainabilityV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.market=(ROOT/'market.js').read_text(encoding='utf-8')

    def test_score_probability_confusion_is_explicitly_rejected(self):
        self.assertIn('não significa 75–80% de upside', self.market)
        self.assertIn('percentil 80 significa melhor posicionamento', self.market)

    def test_evaluation_layers_are_separated(self):
        self.assertIn('COMO LER AS AVALIAÇÕES', self.market)
        self.assertIn('1 · Empresa', self.market)
        self.assertIn('2 · Preço', self.market)
        self.assertIn('3 · Evidência', self.market)
        self.assertIn('4 · Risco', self.market)

    def test_general_weights_are_visible(self):
        self.assertIn("['Qualidade',18]", self.market)
        self.assertIn("['Crescimento',15]", self.market)
        self.assertIn("['Valuation',12]", self.market)
        self.assertIn("['Estabilidade',5]", self.market)

    def test_specialist_models_are_explained(self):
        for phrase in ('Modelo bancário:', 'Modelo de seguros:', 'Modelo REIT:', 'Modelo biotech:', 'Modelo tecnologia/crescimento:'):
            self.assertIn(phrase, self.market)

    def test_valuation_method_and_thresholds_are_explained(self):
        self.assertIn('peso ${num(x.weight)}x', self.market)
        self.assertIn('média ponderada e mediana', self.market)
        self.assertIn('“undervalued” exige pelo menos +25%', self.market)
        self.assertIn('confidence score abaixo de 50', self.market)

if __name__ == '__main__':
    unittest.main(verbosity=2)
