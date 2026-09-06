from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MarketUiPolishContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / 'market-ui-polish.js').read_text(encoding='utf-8')
        cls.loader = (ROOT / 'market-static-universe.js').read_text(encoding='utf-8')

    def test_dossier_watch_is_fixed_beside_persistent_close(self):
        self.assertIn('#marketSheetContent .market-watch--detail', self.source)
        self.assertIn('position:fixed!important', self.source)
        self.assertIn('right:max(calc(env(safe-area-inset-right) + 66px),66px)!important', self.source)
        self.assertIn('width:44px!important', self.source)
        self.assertIn('height:44px!important', self.source)

    def test_politicians_state_is_cleared_before_normal_market_mode_switch(self):
        self.assertIn("[data-politicians-mode]", self.source)
        self.assertIn("[data-market-mode]", self.source)
        self.assertIn("classList.remove('is-active')", self.source)
        self.assertIn("document.addEventListener('click', onClickCapture, true)", self.source)

    def test_no_market_data_or_financial_semantics_changed(self):
        self.assertNotIn('fetch(', self.source)
        self.assertNotIn('score', self.source.lower())
        self.assertNotIn('risk_gate', self.source.lower())
        self.assertNotIn('localStorage', self.source)
        self.assertNotIn('indexedDB', self.source)

    def test_companion_is_reachable_from_loader(self):
        self.assertIn('ensureMarketUiPolish', self.loader)
        self.assertIn('market-ui-polish.js?v=1.0', self.loader)
        self.assertIn("version: '1.6'", self.loader)


if __name__ == '__main__':
    unittest.main(verbosity=2)
