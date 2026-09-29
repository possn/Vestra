from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DashboardPrivacyToggleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = (ROOT / "app.js").read_text(encoding="utf-8")

    def test_toggle_updates_privacy_before_persisting(self):
        start = self.app.index("function toggleDashboardPrivacy()")
        end = self.app.index("\nfunction ", start + 20)
        block = self.app[start:end]
        self.assertIn("applyDashboardPrivacy();", block)
        self.assertIn("saveState();", block)
        self.assertLess(block.index("applyDashboardPrivacy();"), block.index("saveState();"))

    def test_toggle_does_not_force_full_dashboard_render(self):
        start = self.app.index("function toggleDashboardPrivacy()")
        end = self.app.index("\nfunction ", start + 20)
        block = self.app[start:end]
        self.assertNotIn("renderDashboard()", block)
        self.assertNotIn("markViewsDirty", block)

    def test_privacy_mask_is_reversible_without_render(self):
        self.assertIn("const dashboardPrivacyOriginalText = new WeakMap();", self.app)
        self.assertIn("function restoreDashboardMoneyText(root)", self.app)
        apply_start = self.app.index("function applyDashboardPrivacy()")
        apply_end = self.app.index("\nfunction ", apply_start + 20)
        apply_block = self.app[apply_start:apply_end]
        self.assertIn("restoreDashboardMoneyText(view);", apply_block)
        self.assertIn("restoreDashboardMoneyText(passiveBar);", apply_block)


if __name__ == "__main__":
    unittest.main(verbosity=2)
