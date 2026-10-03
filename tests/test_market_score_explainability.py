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

    def test_pillar_strengths_and_weaknesses_stay_visible_without_duplicate_summary(self):
        self.assertIn('SCORE BREAKDOWN', self.market)
        self.assertIn('dossierPillarBand', self.market)
        self.assertIn('DETALHE QUANTITATIVO DOS PILARES', self.market)
        explanation=self.market.split('function scoreExplanation(s)',1)[1].split('function shortDate(v)',1)[0]
        self.assertNotIn('A puxar para cima:', explanation)
        self.assertNotIn('A limitar a avaliação:', explanation)

    def test_coverage_model_and_missing_data_are_visible(self):
        self.assertIn('scoreModelLabel', self.market)
        self.assertIn('Cobertura ${coverage', self.market)
        self.assertIn('não vale zero nem aumenta o peso dos restantes', self.market)
        self.assertIn('entra como neutro 50', self.market)
        self.assertIn('Reliability/Confidence', self.market)

    def test_overview_renders_explanation(self):
        self.assertIn('${scoreExplanation(s)}`;', self.market)
        overview = self.market.split("if(tab==='overview')", 1)[1].split("if(tab==='perspective')", 1)[0]
        self.assertNotIn('Pilares · percentis relativos', overview)

    def test_score_layers_are_explicit(self):
        self.assertIn('1 · Ranking fundamental.', self.market)
        self.assertIn('2 · Qualidade da evidência.', self.market)
        self.assertIn('3 · Travão de risco.', self.market)
        self.assertIn('4 · Valuation, tese e expectativas.', self.market)
        self.assertIn('5 · Decisão de carteira.', self.market)
        self.assertIn('scoreModelWeights', self.market)

    def test_data_quality_separates_coverage_confidence_and_reliability(self):
        self.assertIn('Confiança da evidência', self.market)
        self.assertIn('Fiabilidade do Score', self.market)
        self.assertIn('Cobertura nativa do modelo', self.market)
        self.assertIn('scoreReliabilityLabel', self.market)
        self.assertIn('qualidade e atualidade das fontes', self.market)
        self.assertNotIn('A confiança mede cobertura, não certeza do investimento.', self.market)

    def test_public_score_moderation_is_explained(self):
        self.assertIn('score_raw', self.market)
        self.assertIn('critical_metric_coverage_pct', self.market)
        self.assertIn('score_reliability', self.market)
        self.assertIn('score_cap', self.market)
        self.assertIn('Risk Gate', self.market)

    def test_decision_signal_labels_stay_semantically_separate(self):
        self.assertIn('Convicção sintetiza Score Vestra, valuation, expectativas e direção da tese.', self.market)
        self.assertIn('Confiança mede separadamente a qualidade da evidência', self.market)
        self.assertIn('Risk Gate é um travão independente', self.market)
        self.assertNotIn('Convicção combina Score Vestra, confiança, valuation, expectativas e Risk Gate.', self.market)

    def test_specialist_model_weights_are_visible(self):
        for token in ('growth_tech', 'bank', 'reit', 'insurance', 'utility', 'energy', 'biotech'):
            self.assertIn(token, self.market)
        self.assertIn("['Runway de caixa',25]", self.market)
        self.assertIn("['Caixa líquida',15]", self.market)
        self.assertIn("['Qualidade bancária',22]", self.market)
        self.assertIn("['Qualidade do crédito',10]", self.market)

if __name__ == '__main__':
    unittest.main(verbosity=2)
