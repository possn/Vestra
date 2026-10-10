"""Vestra 2.0: single Home and unified navigation chrome contracts."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class CanonicalHomeTest(unittest.TestCase):
    def test_detail_mode_hides_duplicate_editorial_home(self):
        css = (ROOT / "vestra-intelligence.css").read_text(encoding="utf-8")
        self.assertIn('data-legacy-open="true"]) .v2-home-intro', css)
        self.assertIn('data-legacy-open="true"]) .v2-home-stage__aside', css)
        self.assertIn('data-legacy-open="true"]) .vi-back-to-intelligence', css)

    def test_detail_entry_scrolls_to_visible_context(self):
        js = (ROOT / "vestra-intelligence-home.js").read_text(encoding="utf-8")
        self.assertIn("document.querySelector('#viewDashboard .vi-back-to-intelligence')", js)
        self.assertNotIn("const legacy = document.querySelector('#viewDashboard .dashboard-welcome');", js)
        self.assertIn("document.querySelector('#viewDashboard .v2-detail-chapter-nav')", js)
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('class="v2-detail-chapter-nav"', html)
        self.assertIn('id="v2-history-chapter"', html)

    def test_single_daily_market_news_and_calendar_readings(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        home = html.split('<section id="vestraIntelligenceHome"', 1)[1].split('<div class="vi-back-to-intelligence">', 1)[0]
        self.assertNotIn('class="vi-daily-brief"', home)
        for canonical in ('vi-market-reading', 'vi-events-reading', 'vi-news-reading'):
            self.assertEqual(home.count('class="vi-canonical-card ' + canonical + '"'), 1)

    def test_decisions_precede_secondary_market_readings(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        home = html.split('<section id="vestraIntelligenceHome"', 1)[1].split('<div class="vi-back-to-intelligence">', 1)[0]
        self.assertLess(home.index('class="vi-priorities"'), home.index('class="vi-canonical-sections"'))
        self.assertEqual(home.count('class="vi-priorities"'), 1)

    def test_portfolio_risk_precedes_secondary_market_and_news(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        home = html.split('<section id="vestraIntelligenceHome"', 1)[1].split('<div class="vi-back-to-intelligence">', 1)[0]
        self.assertLess(home.index('class="vi-risk-reading"') if 'class="vi-risk-reading"' in home else home.index('vi-canonical-card vi-risk-reading'), home.index('vi-canonical-card vi-market-reading'))
        self.assertEqual(home.count('vi-canonical-card vi-risk-reading'), 1)

    def test_market_regime_evidence_is_optional_not_removed(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('class="vi-regime-disclosure"', html)
        self.assertIn('data-vestra-market-status', html)
        self.assertIn('vi-regime-grid', html)
        self.assertIn('vestra-intelligence.css?v=31', html)

    def test_context_chapter_follows_decisions_without_duplication(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        home = html.split('<section id="vestraIntelligenceHome"', 1)[1].split('<div class="vi-back-to-intelligence">', 1)[0]
        self.assertEqual(home.count('class="vi-context-chapter"'), 1)
        self.assertLess(home.index('class="vi-priorities"'), home.index('class="vi-context-chapter"'))
        self.assertEqual(home.count('class="vi-canonical-sections"'), 1)

    def test_unified_sidebar_and_cache_generation(self):
        nav = (ROOT / "vestra-navigation-v2.css").read_text(encoding="utf-8")
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('.sidebar{background:#0d2523!important', nav)
        self.assertIn('vestra-navigation-v2.css?v=6', html)
        self.assertIn('vestra-intelligence.css?v=31', html)
        self.assertIn('vestra-intelligence-home.js?v=12', html)

    def test_legacy_drilldown_safari_ink_and_tools_cta(self):
        css = (ROOT / "vestra-intelligence.css").read_text(encoding="utf-8")
        self.assertIn("--v2-detail-ink:#f3f0e7", css)
        self.assertIn("-webkit-text-fill-color:var(--v2-detail-ink)!important", css)
        self.assertIn("#btnToggleDashSecondary{", css)
        self.assertIn("env(safe-area-inset-bottom,0px)", css)

    def test_history_axes_preserve_snapshots_without_mixing_scales(self):
        js = (ROOT / "app.js").read_text(encoding="utf-8")
        self.assertIn('yAxisID: "passive"', js)
        self.assertIn('trendChart.data.datasets[2].yAxisID = "passive"', js)
        self.assertIn('maxTicksLimit: 6', js)
        self.assertIn('passiveAnnual||0', js)
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="trendChart"', html)
        self.assertIn('id="snapshotTable"', html)

if __name__ == "__main__":
    unittest.main()
