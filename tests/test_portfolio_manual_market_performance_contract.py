"""Regression guard: manual portfolio editing and Market first-paint remain responsive."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PortfolioMarketPerformanceContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = (ROOT / "app.js").read_text(encoding="utf-8")
        cls.static = (ROOT / "market-static-universe.js").read_text(encoding="utf-8")
        cls.market = (ROOT / "market.js").read_text(encoding="utf-8")

    def test_market_first_paint_is_not_blocked_by_etf_enrichment(self):
        self.assertIn("beforeReady(); state.loaded = true; onReady(); announceReady(stocks);", self.static)
        self.assertIn("Promise.resolve(etfReady).then(() =>", self.static)
        self.assertNotIn("await etfReady;", self.static)
        self.assertIn("vestra:market-etf-ready", self.static)
        self.assertIn("if(M.loaded && M.mode==='funds') renderPrimary();", self.market)
        self.assertIn("vestra:market-etf-ready", self.market)

    def test_manual_save_confirms_only_after_storage_and_refreshes_dependencies(self):
        section = self.app.split("async function saveItemFromModal() {", 1)[1].split(
            "\nfunction deleteCurrentItem() {", 1
        )[0]
        self.assertIn("await saveStateAsync();", section)
        self.assertLess(section.index("await saveStateAsync();"),
                        section.index('closeModal("modalItem")'))
        self.assertIn("markViewsDirty(RENDERABLE_VIEWS);", section)
        self.assertIn("scheduleRenderView(currentView, { force: false });", section)
        self.assertIn("vestra:portfolio-totals-updated", section)
        self.assertIn("previousItems", section)
        self.assertIn("state.assets = previousItems", section)
        self.assertIn("A guardar", section)
        self.assertNotIn("renderDashboard();\n  renderItems();", section)

    def test_sector_map_build_runs_after_section_switch(self):
        section = self.app.split("function setView(view) {", 1)[1].split(
            "\nfunction openModal(", 1
        )[0]
        self.assertLess(section.index("for (const s of _viewEls) s.hidden"),
                        section.index("ensurePortfolioSectorMap();"))
        self.assertIn("if (currentView !== view) return;", section)


if __name__ == "__main__":
    unittest.main()
