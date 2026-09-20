import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
UI_CORE = (ROOT / "app-ui-core.js").read_text(encoding="utf-8")
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")


class ChartReflowCoalescingTests(unittest.TestCase):
    def test_new_schedule_cancels_superseded_chart_work(self):
        schedule = UI_CORE[
            UI_CORE.index("function cancelChartStabilization()"):
            UI_CORE.index("function installChartReflowGuards()")
        ]
        self.assertIn("cancelChartStabilization();", schedule)
        self.assertIn("cancelAnimationFrame(id)", schedule)
        self.assertIn("clearTimeout(id)", schedule)
        self.assertIn("chartStabilizeTimerIds.push(setTimeout(run, 140))", schedule)
        self.assertIn("chartStabilizeTimerIds.push(setTimeout(run, 420))", schedule)

    def test_chart_dimensions_are_only_written_when_the_height_changes(self):
        prepare = UI_CORE[
            UI_CORE.index("function prepareChartCanvas"):
            UI_CORE.index("let chartStabilizeToken")
        ]
        self.assertIn("wrap.dataset.chartHeightApplied !== appliedHeight", prepare)
        self.assertIn("canvas.dataset.chartHeightApplied !== appliedHeight", prepare)
        self.assertEqual(prepare.count('canvas.setAttribute("height", appliedHeight)'), 1)

    def test_browser_loads_the_new_ui_core_generation(self):
        self.assertIn('app-ui-core.js?v=2.7', INDEX)


if __name__ == "__main__":
    unittest.main()
