from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")
APP = (ROOT / "app.js").read_text(encoding="utf-8")
STYLES = (ROOT / "styles.css").read_text(encoding="utf-8")


class DashboardPrivacyToggleTests(unittest.TestCase):
    def test_privacy_preference_is_read_before_body_render(self):
        head_end = INDEX.index("</head>")
        privacy = INDEX.index("vestra:dashboard-privacy-v1")
        self.assertLess(privacy, head_end)
        self.assertIn("document.documentElement.dataset.dashboardPrivacy = 'hidden'", INDEX)

    def test_dashboard_has_accessible_privacy_button(self):
        self.assertIn('id="btnToggleNetWorthPrivacy"', INDEX)
        self.assertIn('onclick="toggleDashboardPrivacy()"', INDEX)
        self.assertIn('aria-label="Ocultar valor do património"', INDEX)
        self.assertIn('aria-pressed="false"', INDEX)

    def test_hidden_mode_never_writes_real_hero_amounts(self):
        self.assertIn('const DASHBOARD_PRIVACY_KEY = "vestra:dashboard-privacy-v1";', APP)
        self.assertIn('net.textContent = hidden ? "•••••• €" : fmtEUR(t.net);', APP)
        self.assertIn('"Ativos •••••• € | Passivos •••••• €"', APP)
        self.assertIn('const value = hidden', APP)

    def test_toggle_persists_locally_and_only_renders_hero(self):
        start = APP.index("function toggleDashboardPrivacy()")
        end = APP.index("\nfunction renderDashboard()", start)
        block = APP[start:end]
        self.assertIn("localStorage.setItem(DASHBOARD_PRIVACY_KEY", block)
        self.assertIn("renderDashboardHero(", block)
        self.assertNotIn("renderDashboard();", block)

    def test_main_dashboard_render_delegates_hero_privacy(self):
        start = APP.index("function renderDashboard()")
        end = APP.index("/* ─── ALERTA:", start)
        block = APP[start:end]
        self.assertIn("renderDashboardHero(t);", block)
        self.assertNotIn('$("kpiNet").textContent = fmtEUR(t.net)', block)

    def test_privacy_control_has_visible_focus_state(self):
        self.assertIn(".privacy-toggle", STYLES)
        self.assertIn(".privacy-toggle:focus-visible", STYLES)

    def test_runtime_and_styles_are_versioned_for_rollout(self):
        self.assertIn("styles.css?v=20260919v1", INDEX)
        self.assertIn("app.js?v=20260919v1", INDEX)


if __name__ == "__main__":
    unittest.main(verbosity=2)
