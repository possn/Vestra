from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PortfolioUiDataContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.market = (ROOT / 'market.js').read_text(encoding='utf-8')
        cls.ui = (ROOT / 'vestra-portfolio-ui.js').read_text(encoding='utf-8')

    def test_portfolio_summary_exposes_structured_metrics(self):
        for token in (
            'data-vpu-positions="${assets.length}"',
            'data-vpu-research="${rows.length}"',
            'data-vpu-coverage="${researchTotal>0?Math.round(analysed/researchTotal*100):0}"',
        ):
            self.assertIn(token.replace('\\',''), self.market)

    def test_decision_center_exposes_structured_metrics(self):
        for token in (
            'data-vpu-conviction="${conviction==null?\'\':conviction.toFixed(1)}"',
            'data-vpu-risk="${riskBudget.fit==null?\'\':riskBudget.fit}"',
            'data-vpu-review="${review.length}"',
            'data-vpu-state="${esc(decisionState)}"',
        ):
            self.assertIn(token.replace('\\',''), self.market)
        self.assertNotIn('data-vpu-health=', self.market)

    def test_review_total_is_not_confused_with_twelve_preview_or_three_highlights(self):
        self.assertIn('data-queue-pending="${activeItems.length}"', self.market)
        self.assertIn('data-queue-preview="${visible.length}"', self.market)
        self.assertIn('const featured=visible.slice(0,3), more=visible.slice(3)', self.market)
        self.assertIn('market-research-queue-more', self.market)
        self.assertIn('dataset.queuePending', self.ui)
        self.assertIn('de ${m.reviewTotal} na fila', self.ui)
        self.assertIn('Ver destaques', self.ui)

    def test_portfolio_ui_prefers_structured_metrics_before_text_fallbacks(self):
        block = self.ui.split('function metrics(c){', 1)[1].split('function status(m){', 1)[0]
        self.assertIn("summary?.dataset.vpuPositions", block)
        self.assertIn("summary?.dataset.vpuResearch", block)
        self.assertIn("summary?.dataset.vpuCoverage", block)
        self.assertIn("dc?.dataset.vpuConviction", block)
        self.assertIn("dc?.dataset.vpuRisk", block)
        self.assertLess(block.index("summary?.dataset.vpuPositions"), block.index("kpiByLabel(c,'Posições')"))
        self.assertLess(block.index("dc?.dataset.vpuConviction"), block.index("dcTxt.match(/CONVICÇÃO"))


if __name__ == '__main__':
    unittest.main(verbosity=2)
