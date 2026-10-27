from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class WeeklyHistoryControlsTests(unittest.TestCase):
    def test_navigation_recovers_after_dashboard_rerenders_week(self):
        nav = (ROOT / "dashboard-weekly-events-navigation.js").read_text(encoding="utf-8")
        core = (ROOT / "dashboard-weekly-events.js").read_text(encoding="utf-8")
        loader = (ROOT / "market-static-universe.js").read_text(encoding="utf-8")
        self.assertIn("card.replaceChildren()", core)
        self.assertIn("source: 'weekly-events'", core)
        self.assertIn("'vestra:dashboard-signal-updated'", nav)
        self.assertIn("event?.detail?.source === 'weekly-events'", nav)
        self.assertIn("decorate();", nav)
        self.assertIn("dashboard-weekly-events-navigation.js?v=1.3", loader)

    def test_routine_rerenders_keep_selected_past_week(self):
        core = (ROOT / "dashboard-weekly-events.js").read_text(encoding="utf-8")
        self.assertIn("const nav = window.VestraWeeklyEventsNavigation;", core)
        self.assertIn("options.now || (nav?.shiftedDate ? nav.shiftedDate(new Date()) : new Date())", core)
        self.assertIn("window.addEventListener?.('vestra:market-ready',()=>{ render(expandedContext || {});", core)

    def test_sunday_week_offset_not_mislabelled_today(self):
        core = (ROOT / "dashboard-weekly-events.js").read_text(encoding="utf-8")
        loader = (ROOT / "market-static-universe.js").read_text(encoding="utf-8")
        self.assertIn("day.textContent=dayLabel(event.date,new Date());", core)
        self.assertNotIn("day.textContent=dayLabel(event.date,now);", core)
        self.assertIn("dashboard-weekly-events.js?v=3.7", loader)

    def test_history_navigation_keeps_week_offset_and_result_detail(self):
        nav = (ROOT / "dashboard-weekly-events-navigation.js").read_text(encoding="utf-8")
        core = (ROOT / "dashboard-weekly-events.js").read_text(encoding="utf-8")
        self.assertIn("weekOffset = Math.max(-MAX_WEEK_OFFSET", nav)
        self.assertIn("shiftedDate(base)", nav)
        self.assertIn("makeButton('prev'", nav)
        self.assertIn("makeButton('next'", nav)
        self.assertIn("makeButton('today'", nav)
        self.assertIn("findMacroEventById", core)
        self.assertIn("resultMetrics: normaliseOfficialMetrics", core)


if __name__ == "__main__":
    unittest.main()
