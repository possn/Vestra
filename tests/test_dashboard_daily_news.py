from pathlib import Path
import json
import subprocess
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
        cls.index = (ROOT / "index.html").read_text(encoding="utf-8")
        cls.feed_refresh = (ROOT / "scripts" / "refresh_dashboard_news.py").read_text(encoding="utf-8")
        cls.feed_workflow = (ROOT / ".github" / "workflows" / "update-dashboard-feeds.yml").read_text(encoding="utf-8")

    def test_dashboard_feed_has_independent_lightweight_refresh(self):
        self.assertIn('from news import _build_dashboard_digest', self.feed_refresh)
        self.assertIn('COMPANY_RETENTION_HOURS = 36', self.feed_refresh)
        self.assertIn('name: Update dashboard news', self.feed_workflow)
        self.assertIn('cron: "*/30 * * * *"', self.feed_workflow)
        self.assertIn('PYTHONPATH=scripts python scripts/refresh_dashboard_news.py', self.feed_workflow)
        self.assertNotIn('macro_calendar_transport.py', self.feed_workflow)
        self.assertIn('PUBLISH_SUPERSEDE_COMMIT_PREFIX="Actualização notícias Dashboard ("', self.feed_workflow)

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
        self.assertIn("dashboard-daily-news.js?v=1.3", self.loader)
        self.assertIn("ensureDashboardDailyNews()", self.loader)
        self.assertIn('"./dashboard-daily-news.js"', self.sw)
        self.assertIn('"./dashboard-daily-news.css"', self.sw)
        self.assertIn("dashboard-daily-news.css?v=1.0", self.runtime)
        self.assertIn("version: '1.3'", self.runtime)

    def test_news_runtime_is_network_first_so_interaction_fixes_are_not_stale(self):
        network_first = self.sw.split('const BOOTSTRAP_NETWORK_FIRST = new Set([', 1)[1].split(']);', 1)[0]
        self.assertIn('"dashboard-daily-news.js"', network_first)
        self.assertIn('if (request.destination === "script" && BOOTSTRAP_NETWORK_FIRST.has(assetName))', self.sw)
        self.assertIn('event.respondWith(networkFirst(request)); return;', self.sw)

    def test_card_mount_targets_the_live_dashboard_structure(self):
        self.assertIn('id="viewDashboard"', self.index)
        self.assertIn('class="card kpi-quick"', self.index)
        self.assertIn("document.getElementById('viewDashboard')", self.runtime)
        self.assertIn("dashboard.querySelector('.kpi-quick')", self.runtime)
        self.assertIn("mount.parent.insertBefore(next, mount.before)", self.runtime)
        self.assertIn("mount.parent.appendChild(next)", self.runtime)
        self.assertNotIn("getElementById('quickTools')", self.runtime)
        self.assertNotIn("getElementById('passiveIncomeSection')", self.runtime)
        self.assertNotIn("getElementById('portfolioEvolutionCard')", self.runtime)

    def test_render_is_idempotent_so_ios_taps_keep_the_same_anchor_node(self):
        self.assertIn("let renderedMarkup = ''", self.runtime)
        self.assertIn("const markup = cardHtml()", self.runtime)
        self.assertIn("if (existing && markup === renderedMarkup) return true", self.runtime)
        self.assertIn("existing.parentElement === mount.parent", self.runtime)
        self.assertIn("existing.nextElementSibling === mount.before", self.runtime)
        self.assertIn("existing.isEqualNode(next)", self.runtime)
        self.assertIn("new MutationObserver(queueRender)", self.runtime)

    def test_card_stays_compact_and_has_external_link_hardening(self):
        self.assertIn('id="vestraDailyNewsCard"', self.runtime)
        self.assertIn('target="_blank" rel="noopener noreferrer"', self.runtime)
        self.assertIn("function safeNewsUrl(value)", self.runtime)
        self.assertIn("['http:', 'https:'].includes(url.protocol)", self.runtime)
        self.assertIn('class="vestra-daily-news-item is-disabled"', self.runtime)
        self.assertIn(".vestra-daily-news-card{", self.css)

    def test_outbound_news_records_short_lived_return_context_without_hijacking_navigation(self):
        self.assertIn("const NEWS_RETURN_KEY = 'vestra:daily-news-return-v1'", self.runtime)
        self.assertIn("const NEWS_RETURN_TTL_MS = 30 * 60 * 1000", self.runtime)
        self.assertIn("function rememberNewsReturn()", self.runtime)
        self.assertIn("localStorage.setItem(NEWS_RETURN_KEY, JSON.stringify(context))", self.runtime)
        self.assertIn("rememberExternalReturnContext", self.runtime)
        self.assertIn("const EXTERNAL_RETURN_KEY = 'vestra:external-return-v1'", self.runtime)
        self.assertIn("a.vestra-daily-news-item[href]", self.runtime)
        self.assertIn("rememberNewsReturn()", self.runtime)
        self.assertNotIn("event.preventDefault()", self.runtime)
        self.assertNotIn("window.open(", self.runtime)

    def test_return_context_survives_early_ios_resume_events_before_reload(self):
        self.assertIn("const NEWS_RETURN_RESUME_GRACE_MS = 30 * 1000", self.runtime)
        self.assertIn("function schedulePendingNewsReturnCleanup()", self.runtime)
        self.assertIn("window.addEventListener?.('focus', resume)", self.runtime)
        self.assertIn("window.addEventListener?.('pageshow', resume)", self.runtime)
        self.assertIn("void load(true)", self.runtime)
        self.assertIn("document.visibilityState === 'visible'", self.runtime)
        self.assertIn("setTimeout(() =>", self.runtime)
        self.assertIn("NEWS_RETURN_RESUME_GRACE_MS", self.runtime)
        self.assertNotIn("window.addEventListener?.('focus', clearPendingNewsReturn)", self.runtime)
        self.assertNotIn("window.addEventListener?.('pageshow', clearPendingNewsReturn)", self.runtime)

    def test_return_context_restores_scroll_after_real_reload(self):
        self.assertIn("function restoreNewsReturnContext()", self.runtime)
        self.assertIn("window.__vestraDailyNewsReturnContext", self.runtime)
        self.assertIn("window.scrollTo(0, scrollY)", self.runtime)

    def test_outbound_news_url_sanitizer_rejects_script_and_data_schemes(self):
        source = json.dumps(self.runtime)
        script = f"""
          global.window = {{}};
          global.document = {{
            readyState: 'loading',
            baseURI: 'https://vestra.local/app/',
            addEventListener() {{}}
          }};
          eval({source});
          const safe = window.VestraDashboardDailyNews.safeNewsUrl;
          console.log(JSON.stringify({{
            https: safe('https://example.com/story'),
            http: safe('http://example.com/story'),
            relative: safe('/story'),
            javascript: safe('javascript:alert(1)'),
            data: safe('data:text/html,<script>alert(1)</script>'),
            malformed: safe('http://[invalid')
          }}));
        """
        result = subprocess.run(
            ["node", "-e", script],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        urls = json.loads(result.stdout.strip())
        self.assertEqual(urls["https"], "https://example.com/story")
        self.assertEqual(urls["http"], "http://example.com/story")
        self.assertEqual(urls["relative"], "https://vestra.local/story")
        self.assertEqual(urls["javascript"], "")
        self.assertEqual(urls["data"], "")
        self.assertEqual(urls["malformed"], "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
