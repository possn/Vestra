from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DashboardPrivacyTests(unittest.TestCase):
    def test_dashboard_has_persistent_privacy_toggle(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        app = (ROOT / "app.js").read_text(encoding="utf-8")
        self.assertIn('id="btnDashboardPrivacy"', html)
        self.assertIn('onclick="toggleDashboardPrivacy()"', html)
        self.assertIn('state.settings.hideDashboardValues', app)
        self.assertIn('function dashboardPrivacyEnabled()', app)
        self.assertIn('function toggleDashboardPrivacy()', app)
        self.assertIn('saveState();', app.split('function toggleDashboardPrivacy()', 1)[1].split('}', 1)[0])

    def test_privacy_masks_dashboard_euro_values_but_not_percentages(self):
        app = (ROOT / "app.js").read_text(encoding="utf-8")
        block = app.split('function maskDashboardMoneyText(root)', 1)[1].split('function applyDashboardPrivacy()', 1)[0]
        self.assertIn('source.includes("€")', block)
        self.assertIn('•••• €', block)
        self.assertNotIn('%', block)
        apply_block = app.split('function applyDashboardPrivacy()', 1)[1].split('function toggleDashboardPrivacy()', 1)[0]
        self.assertIn('maskDashboardMoneyText(view)', apply_block)
        self.assertIn('maskDashboardMoneyText(document.getElementById("passivebar"))', apply_block)

    def test_absolute_trend_chart_is_hidden_in_privacy_mode(self):
        app = (ROOT / "app.js").read_text(encoding="utf-8")
        block = app.split('function applyDashboardPrivacy()', 1)[1].split('function toggleDashboardPrivacy()', 1)[0]
        self.assertIn('document.getElementById("trendChart")', block)
        self.assertIn('trend.style.visibility = hidden ? "hidden" : ""', block)
        self.assertIn('"Valores ocultos"', block)

    def test_passive_bar_refresh_respects_privacy(self):
        app = (ROOT / "app.js").read_text(encoding="utf-8")
        block = app.split('function updatePassiveBar()', 1)[1].split('function ', 1)[0]
        self.assertIn('currentView === "dashboard" && dashboardPrivacyEnabled()', block)
        self.assertIn('maskDashboardMoneyText(barA)', block)
        self.assertIn('maskDashboardMoneyText(barM)', block)

    def test_privacy_control_has_mobile_compact_style(self):
        css = (ROOT / "styles.css").read_text(encoding="utf-8")
        self.assertIn('.dashboard-privacy-toggle{', css)
        self.assertIn('@media(max-width:520px)', css)
        self.assertIn('.dashboard-privacy-toggle span{display:none}', css)


if __name__ == "__main__":
    unittest.main(verbosity=2)
