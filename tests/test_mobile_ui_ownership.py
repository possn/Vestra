from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class MobileUiOwnershipTests(unittest.TestCase):
    def test_app_js_is_the_single_sidebar_runtime_owner(self):
        app = read("app.js")
        mobile = read("mobile-ui-refresh.js")

        for marker in (
            "function openSidebar()",
            "function closeSidebar()",
            "function wireSidebar()",
            'toggle.addEventListener("click", openSidebar)',
            'backdrop.addEventListener("click", closeSidebar)',
        ):
            self.assertIn(marker, app, marker)

        for forbidden in (
            "function setSidebarOpen(",
            "function ensureSidebarRuntime(",
            "vestraMobileDrawer",
            "setSidebarOpen(true)",
            "setSidebarOpen(false)",
        ):
            self.assertNotIn(forbidden, mobile, forbidden)

    def test_mobile_refresh_remains_presentation_only(self):
        mobile = read("mobile-ui-refresh.js")
        self.assertIn("ensureStyles();", mobile)
        self.assertIn("normalizeTopbarIcons();", mobile)
        self.assertIn("ensureShortcuts();", mobile)
        self.assertIn("presentation-only", mobile)


if __name__ == "__main__":
    unittest.main(verbosity=2)
