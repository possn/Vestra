from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "dashboard-market-sentiment.js").read_text(encoding="utf-8")
CSS = (ROOT / "dashboard-market-sentiment.css").read_text(encoding="utf-8")
LOADER = (ROOT / "market-static-universe.js").read_text(encoding="utf-8")
SW = (ROOT / "sw.js").read_text(encoding="utf-8")


class DashboardMarketSentimentTests(unittest.TestCase):
    def test_runtime_is_reachable_without_blocking_market_load(self):
        self.assertIn("ensureDashboardMarketSentiment", LOADER)
        self.assertIn("dashboard-market-sentiment.js?v=1.2", LOADER)
        tail = LOADER[LOADER.index("// Dashboard/mobile companions remain eager"):]
        self.assertIn("ensureDashboardMarketSentiment();", tail)
        self.assertIn("requestIdleCallback", JS)
        self.assertIn("setTimeout(run,700)", JS)

    def test_score_methodology_is_explicit_and_price_derived(self):
        for ticker in ("ACWI", "SPY", "QQQ", "IWM", "EFA", "EEM", "^VIX"):
            self.assertIn(ticker, JS)
        self.assertIn("weightedMetric(details,'trend'", JS)
        self.assertIn("weightedMetric(details,'momentum'", JS)
        self.assertIn("weightedMetric(details,'participation'", JS)
        self.assertIn("35% tendência", JS)
        self.assertIn("30% momentum", JS)
        self.assertIn("20% participação proxy", JS)
        self.assertIn("15% VIX", JS)
        self.assertIn("Não usa breadth real", JS)

    def test_editorial_gauge_and_mobile_contract_exist(self):
        self.assertIn("MARKET SENTIMENT · VESTRA READ", JS)
        self.assertIn("O QUE ESTÁS A VER.", JS)
        self.assertIn("dms-gauge", CSS)
        self.assertIn("font-family:Georgia", CSS)
        self.assertIn("@media(max-width:560px)", CSS)
        self.assertIn("@media(max-width:360px)", CSS)

    def test_methodology_is_progressively_disclosed(self):
        self.assertIn("expanded:false", JS)
        self.assertIn("data-dms-detail-toggle", JS)
        self.assertIn("Ver como é calculado", JS)
        self.assertIn("dms-detail", JS)
        self.assertIn(".dms-detail[hidden]", CSS)
        self.assertIn("version:'1.2'", JS)

    def test_service_worker_tracks_companion(self):
        self.assertIn("./dashboard-market-sentiment.js", SW)
        self.assertIn("./dashboard-market-sentiment.css", SW)


if __name__ == "__main__":
    unittest.main(verbosity=2)
