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
        self.assertIn("dashboard-market-sentiment.js?v=1.8-foreground", LOADER)
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
        self.assertIn("version:'1.7'", JS)

    def test_aaii_retail_sentiment_is_integrated_without_a_second_dashboard_card(self):
        data = (ROOT / "data" / "aaii-sentiment.json").read_text(encoding="utf-8")
        workflow = (ROOT / ".github" / "workflows" / "update-aaii-sentiment.yml").read_text(encoding="utf-8")
        refresh = (ROOT / "scripts" / "refresh_aaii_sentiment.py").read_text(encoding="utf-8")
        self.assertIn("AAII_REFRESH_INTERVAL_MS=15*60*1000", JS)
        self.assertIn("window.addEventListener('focus',()=>loadAaii())", JS)
        self.assertIn("visibilitychange", JS)
        self.assertIn("loadAaii(true);loadCnn()", JS)
        self.assertIn("AAII · RETAIL SENTIMENT", JS)
        self.assertIn("Ver semanas anteriores", JS)
        self.assertIn("data/aaii-sentiment.json", JS)
        self.assertIn("function aaiiWeekCard", JS)
        self.assertIn("dms-aaii-weekcard", JS)
        self.assertIn("aaiiExpanded:false", JS)
        self.assertIn("addEventListener(\'toggle\'", JS)
        self.assertIn(".dms-aaii-weekcard", CSS)
        self.assertIn('"weeks"', data)
        self.assertIn('"latest_published"', data)
        self.assertIn("sent_results?adv=yes", refresh)
        self.assertIn("AAII historical source stale", refresh)
        self.assertIn("Dados AAII desatualizados", JS)
        self.assertIn("ageDays>8", JS)
        self.assertIn('15 15 * * *', workflow)
        self.assertIn("age <= 8", workflow)
        self.assertNotIn('15 15 * * 4', workflow)
        self.assertNotIn('15 15 * * 5', workflow)
        self.assertIn("./data/aaii-sentiment.json", SW)

    def test_quote_freshness_is_visible_and_not_the_cache_timestamp(self):
        self.assertIn('function priceFreshness(details)', JS)
        self.assertIn('latestDates.sort()[0]', JS)
        self.assertIn('Cotações até', JS)
        self.assertIn('priceFreshness:freshness', JS)
        self.assertIn('Dados antigos', JS)

    def test_market_read_does_not_invent_zero_for_missing_values(self):
        self.assertIn("if(v===null||v===undefined||v==='') return null", JS)
        self.assertIn("if(totalWeight<.8) return null", JS)

    def test_market_read_coverage_and_freshness_guard_live_and_cache(self):
        self.assertIn("freshness.coverage<6", JS)
        self.assertIn("daysOld>5", JS)
        self.assertIn("freshness?.coverage>=6", JS)
        self.assertIn("age<=5", JS)
        self.assertIn("S.data=null;", JS)
        self.assertIn("Leitura indisponível: cobertura ou frescura insuficiente", JS)

    def test_service_worker_tracks_companion(self):
        self.assertIn("./dashboard-market-sentiment.js", SW)
        self.assertIn("./dashboard-market-sentiment.css", SW)


if __name__ == "__main__":
    unittest.main(verbosity=2)
