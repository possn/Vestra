from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class MarketValuationExplainabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.market=(ROOT/'market.js').read_text(encoding='utf-8')

    def test_methods_show_relative_weights(self):
        self.assertIn('peso ${num(x.weight)}×', self.market)

    def test_peer_relative_formula_is_explained(self):
        self.assertIn('preço atual × P/E mediano do setor ÷ P/E da empresa', self.market)
        self.assertIn('mediana do próprio setor', self.market)

    def test_range_mechanics_are_explained(self):
        self.assertIn('banda mínima é ±12%', self.market)
        self.assertIn('apenas um é ±18%', self.market)
        self.assertIn('máximo de ±28%', self.market)

    def test_signal_thresholds_and_risk_override_are_explained(self):
        self.assertIn('“Undervalued” exige pelo menos +25%', self.market)
        self.assertIn('“Overvalued” começa em −20%', self.market)
        self.assertIn('confidence score &lt;50', self.market)
        self.assertIn('transforma o sinal em “Uncertain”', self.market)

    def test_not_intrinsic_or_analyst_target(self):
        self.assertIn('Não é DCF, NAV inferido, target de analistas nem preço futuro previsto', self.market)

if __name__ == '__main__':
    unittest.main(verbosity=2)
