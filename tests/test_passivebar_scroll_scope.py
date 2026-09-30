from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.js").read_text(encoding="utf-8")


class PassiveBarScrollScopeTests(unittest.TestCase):
    def test_scroll_work_only_runs_where_passive_bar_is_visible(self):
        marker = 'The passive bar only exists on Dashboard/Portfolio.'
        self.assertIn(marker, APP)
        section = APP[APP.index(marker):APP.index(marker) + 1100]
        self.assertIn('currentView !== "dashboard" && currentView !== "assets"', section)
        self.assertIn('document.body.classList.remove("is-scrolling")', section)
        self.assertIn('return;', section)
        self.assertIn('scheduleFixedBarSync()', section)

    def test_scoped_scroll_listener_stays_passive(self):
        marker = 'The passive bar only exists on Dashboard/Portfolio.'
        section = APP[APP.index(marker)-120:APP.index(marker) + 1300]
        self.assertIn('window.addEventListener("scroll"', section)
        self.assertIn('{ passive: true }', section)


if __name__ == "__main__":
    unittest.main(verbosity=2)
