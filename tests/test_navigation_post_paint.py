from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.js").read_text(encoding="utf-8")


class NavigationPostPaintTests(unittest.TestCase):
    def test_visible_section_switch_stays_synchronous(self):
        self.assertIn("for (const s of _viewEls) s.hidden = s.dataset.view !== view;", APP)

    def test_dirty_view_render_yields_one_paint(self):
        start = APP.index("// Phase 2 (post-paint)")
        block = APP[start:start + 1400]
        raf = block.index("requestAnimationFrame(() => {")
        task = block.index("setTimeout(() => {")
        render = block.index("renderView(view, { force: false, sync: true });")
        self.assertLess(raf, task)
        self.assertLess(task, render)
        self.assertIn("if (currentView !== view) return;", block)

    def test_navigation_does_not_reintroduce_double_raf(self):
        start = APP.index("// Phase 2 (post-paint)")
        block = APP[start:start + 1400]
        self.assertEqual(block.count("requestAnimationFrame(() => {"), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
