from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MarketRuntimeEarlyModeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.loader = (ROOT / 'market-runtime-loader.js').read_text(encoding='utf-8')
        cls.index = (ROOT / 'index.html').read_text(encoding='utf-8')

    def test_loader_captures_mode_clicks_before_core_exists(self):
        self.assertIn("let pendingMode = '';", self.loader)
        self.assertIn("event.target?.closest?.('[data-market-mode]')", self.loader)
        self.assertIn("pendingMode = String(button.dataset.marketMode || '').trim();", self.loader)
        self.assertIn("ensure({ loadData: true }).catch(() => {});", self.loader)

    def test_pending_mode_is_replayed_after_core_load(self):
        self.assertIn('function replayPendingMode()', self.loader)
        self.assertIn('replayPendingMode();', self.loader)
        self.assertIn("button.dispatchEvent(new MouseEvent('click'", self.loader)

    def test_bootstrap_uses_current_runtime_loader_version(self):
        self.assertIn('market-runtime-loader.js?v=1.5', self.index)
        self.assertIn("version: '1.5'", self.loader)


if __name__ == '__main__':
    unittest.main(verbosity=2)
