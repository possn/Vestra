from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DashboardUiRefreshContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / "dashboard-ui-refresh.js").read_text(encoding="utf-8")
        cls.loader = (ROOT / "market-static-universe.js").read_text(encoding="utf-8")

    def test_history_is_collapsed_by_default(self):
        self.assertIn("let historyOpen = false", self.source)
        self.assertIn("table.hidden = !historyOpen", self.source)
        self.assertIn("Ver histórico", self.source)
        self.assertIn("Fechar", self.source)

    def test_dashboard_pulse_uses_local_history_only(self):
        self.assertIn("getState()?.history", self.source)
        self.assertIn("7 dias", self.source)
        self.assertIn("30 dias", self.source)
        self.assertIn("Máximo 90d", self.source)
        self.assertNotIn("fetch(", self.source)
        self.assertNotIn("stocks.json", self.source)

    def test_cashflow_icon_forces_text_presentation(self):
        self.assertIn("#navCashflow .navico", self.source)
        self.assertIn("↕︎", self.source)

    def test_companion_is_reachable_from_static_loader(self):
        self.assertIn("ensureDashboardUiRefresh", self.loader)
        self.assertIn("dashboard-ui-refresh.js?v=1.0", self.loader)
        self.assertIn("version: '1.5'", self.loader)


if __name__ == "__main__":
    unittest.main(verbosity=2)
