from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class UiVisualPolishContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / 'ui-visual-polish.js').read_text(encoding='utf-8')
        cls.styles = (ROOT / 'ui-visual-polish.css').read_text(encoding='utf-8')
        cls.loader = (ROOT / 'market-static-universe.js').read_text(encoding='utf-8')

    def test_polish_is_presentation_only(self):
        for forbidden in ('fetch(', 'localStorage', 'indexedDB', 'state.', 'score', 'risk_gate'):
            self.assertNotIn(forbidden, self.source)

    def test_static_styles_live_outside_runtime_javascript(self):
        self.assertIn("link.rel = 'stylesheet'", self.source)
        self.assertIn("ui-visual-polish.css?v=1.0", self.source)
        self.assertNotIn('style.textContent = `', self.source)

    def test_nested_cards_are_visually_quieter_without_hiding_content(self):
        self.assertIn('#viewDashboard .card .card', self.styles)
        self.assertIn('#viewCashflow .card .card', self.styles)
        self.assertIn('#marketSheetContent .market-detail-card', self.styles)
        self.assertIn('#marketSheetContent .market-metric', self.styles)
        compact = self.styles.replace(' ', '')
        for forbidden in (
            '#viewDashboard{display:none',
            '#viewCashflow{display:none',
            '#marketSheetContent{display:none',
            '#viewDashboard{visibility:hidden',
            '#viewCashflow{visibility:hidden',
            '#marketSheetContent{visibility:hidden',
        ):
            self.assertNotIn(forbidden, compact)

    def test_interactions_keep_accessibility_and_reduced_motion(self):
        self.assertIn(':focus-visible', self.styles)
        self.assertIn('@media(prefers-reduced-motion:reduce)', self.styles)
        self.assertIn('touch-action:manipulation', self.styles)

    def test_loader_reaches_cache_busted_companion(self):
        self.assertIn('ensureUiVisualPolish', self.loader)
        self.assertIn('ui-visual-polish.js?v=1.1', self.loader)
        self.assertIn("version: '1.9'", self.loader)
        self.assertIn("version:'1.1'", self.source)


if __name__ == '__main__':
    unittest.main(verbosity=2)
