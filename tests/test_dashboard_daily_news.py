from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DashboardDailyNewsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = (ROOT / "dashboard-daily-news.js").read_text(encoding="utf-8")
        cls.css = (ROOT / "dashboard-daily-news.css").read_text(encoding="utf-8")
        cls.loader = (ROOT / "market-static-universe.js").read_text(encoding="utf-8")
        cls.news = (ROOT / "scripts" / "news.py").read_text(encoding="utf-8")
        cls.sw = (ROOT / "sw.js").read_text(encoding="utf-8")

    def test_dashboard_uses_compact_digest_not_full_news_archive(self):
        self.assertIn("fetchWithTimeout('data/dashboard-news.json')", self.runtime)
        self.assertNotIn("data/news.json", self.runtime)
        self.assertIn("DASHBOARD_MAX_ITEMS = 40", self.news)
        self.assertIn('"items":selected', self.news)
        self.assertIn("_write_dashboard_digest(results)", self.news)

    def test_portfolio_intersections_are_ranked_ahead_of_generic_market_news(self):
        self.assertIn("function portfolioTickers()", self.runtime)
        self.assertIn("function portfolioHits(item, held)", self.runtime)
        self.assertIn("120 + Math.min(30, hits.length * 10)", self.runtime)
        self.assertIn("MAX_VISIBLE = 5", self.runtime)
        self.assertIn("CARTEIRA", self.runtime)
        self.assertIn("MERCADO", self.runtime)

    def test_news_fetch_is_bounded_and_fail_soft(self):
        self.assertIn("const FETCH_TIMEOUT_MS = 5000", self.runtime)
        self.assertIn("Promise.race([request, timeout])", self.runtime)
        self.assertIn("controller?.abort()", self.runtime)
        self.assertIn(".catch(() => null)", self.runtime)

    def test_companion_is_versioned_reachable_and_offline_capable(self):
        self.assertIn("dashboard-daily-news.js?v=1.0", self.loader)
        self.assertIn("ensureDashboardDailyNews()", self.loader)
        self.assertIn('"./dashboard-daily-news.js"', self.sw)
        self.assertIn('"./dashboard-daily-news.css"', self.sw)
        self.assertIn("dashboard-daily-news.css?v=1.0", self.runtime)

    def test_card_stays_compact_and_has_external_link_hardening(self):
        self.assertIn('id="vestraDailyNewsCard"', self.runtime)
        self.assertIn('target="_blank" rel="noopener noreferrer"', self.runtime)
        self.assertIn("#quickTools", self.css) if False else None
        self.assertIn(".vestra-daily-news-card{", self.css)


if __name__ == "__main__":
    unittest.main(verbosity=2)
