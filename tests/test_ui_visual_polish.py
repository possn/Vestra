from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class UiVisualPolishContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / 'ui-visual-polish.js').read_text(encoding='utf-8')
        cls.loader = (ROOT / 'market-static-universe.js').read_text(encoding='utf-8')

    def test_polish_is_presentation_only(self):
        for forbidden in ('fetch(', 'localStorage', 'indexedDB', 'state.', 'score', 'risk_gate'):
            self.assertNotIn(forbidden, self.source)

    def test_nested_cards_are_visually_quieter_without_hiding_content(self):
        self.assertIn('#viewDashboard .card .card', self.source)
        self.assertIn('#viewCashflow .card .card', self.source)
        self.assertIn('#marketSheetContent .market-detail-card', self.source)
        self.assertIn('#marketSheetContent .market-metric', self.source)
        for forbidden in (
            '#viewDashboard{display:none',
            '#viewCashflow{display:none',
            '#marketSheetContent{display:none',
            '#viewDashboard{visibility:hidden',
            '#viewCashflow{visibility:hidden',
            '#marketSheetContent{visibility:hidden',
        ):
            self.assertNotIn(forbidden, self.source.replace(' ', ''))

    def test_interactions_keep_accessibility_and_reduced_motion(self):
        self.assertIn(':focus-visible', self.source)
        self.assertIn('@media(prefers-reduced-motion:reduce)', self.source)
        self.assertIn('touch-action:manipulation', self.source)

    def test_loader_reaches_cache_busted_companion(self):
        self.assertIn('ensureUiVisualPolish', self.loader)
        self.assertIn('ui-visual-polish.js?v=1.0', self.loader)
        self.assertIn("version: '1.7'", self.loader)


if __name__ == '__main__':
    unittest.main(verbosity=2)
