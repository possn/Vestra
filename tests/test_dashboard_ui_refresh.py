from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DashboardUiRefreshContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / "dashboard-ui-refresh.js").read_text(encoding="utf-8")
        cls.loader = (ROOT / "market-static-universe.js").read_text(encoding="utf-8")
        cls.utils = (ROOT / "app-utils.js").read_text(encoding="utf-8")
        cls.dividend_normalization = (ROOT / "app-broker-normalization.js").read_text(encoding="utf-8")

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

    def test_dashboard_reuses_shared_presentation_helpers(self):
        self.assertIn("const shared = window.VestraUtils", self.source)
        self.assertIn("finiteOrNull: num", self.source)
        self.assertIn("parseLocalDay: parseDay", self.source)
        self.assertIn("canonicalTicker", self.source)
        self.assertIn("shared.formatMoney", self.source)
        self.assertIn("shared.formatPercent", self.source)
        self.assertNotIn("const text = value =>", self.source)
        self.assertNotIn("function parseDay(value)", self.source)
        self.assertNotIn("function canonicalTicker(value)", self.source)
        for helper in ("finiteOrNull", "parseLocalDay", "formatMoney", "formatPercent", "canonicalTicker"):
            self.assertIn(helper, self.utils)

    def test_dashboard_reuses_canonical_dividend_net_normalization(self):
        self.assertIn("window.VestraBrokerNormalization", self.source)
        self.assertIn("getDividendNet", self.source)
        self.assertIn("net: getDividendNet(dividend)", self.source)
        self.assertNotIn("function dividendNet(dividend)", self.source)
        self.assertIn("function getDividendNet(d)", self.dividend_normalization)

    def test_passive_income_grid_has_a_real_30_day_dividend_insight(self):
        self.assertIn("dashboardUpcomingDividendsTile", self.source)
        self.assertIn("Próximos 30 dias", self.source)
        self.assertIn("sem pagamentos previstos", self.source)
        self.assertIn("_yahooDiv?.payDate", self.source)
        self.assertIn("latestObservedPaymentFor", self.source)
        self.assertIn("getDividendNet", self.source)
        self.assertNotIn("_yahooDiv?.rate /", self.source)

    def test_negative_return_is_presented_as_integrated_health_card_without_changing_trigger(self):
        self.assertIn("negReturnAlert", self.source)
        self.assertIn("dashboard-health-card", self.source)
        self.assertIn("Saúde do património", self.source)
        self.assertIn("annual >= -5", self.source)
        self.assertIn("Abaixo da inflação", self.source)
        self.assertNotIn("⚠️", self.source)

    def test_cashflow_icon_forces_text_presentation(self):
        self.assertIn("#navCashflow .navico", self.source)
        self.assertIn("↕︎", self.source)

    def test_companion_is_reachable_from_static_loader(self):
        self.assertIn("ensureDashboardUiRefresh", self.loader)
        self.assertIn("dashboard-ui-refresh.js?v=1.3", self.loader)
        self.assertIn("version: '1.9'", self.loader)
        self.assertIn("version: '1.3'", self.source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
