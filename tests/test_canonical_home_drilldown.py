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

    def test_market_news_and_week_precede_portfolio_exploration(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        home = html.split('<section id="vestraIntelligenceHome"', 1)[1].split('<div class="vi-back-to-intelligence">', 1)[0]
        self.assertLess(home.index('vi-canonical-card vi-market-reading'), home.index('vi-canonical-card vi-news-reading'))
        self.assertLess(home.index('vi-canonical-card vi-news-reading'), home.index('vi-canonical-card vi-events-reading'))
        self.assertLess(home.index('vi-canonical-card vi-events-reading'), home.index('class="vi-priorities"'))
        self.assertEqual(home.count('class="vi-priorities"'), 1)

    def test_portfolio_risk_follows_primary_reading(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        home = html.split('<section id="vestraIntelligenceHome"', 1)[1].split('<div class="vi-back-to-intelligence">', 1)[0]
        self.assertLess(home.index('class="vi-priorities"'), home.index('vi-canonical-card vi-risk-reading'))
        self.assertEqual(home.count('vi-canonical-card vi-risk-reading'), 1)

    def test_market_regime_evidence_is_optional_not_removed(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('class="vi-regime-disclosure"', html)
        self.assertIn('data-vestra-market-status', html)
        self.assertIn('vi-regime-grid', html)
        self.assertIn('vestra-intelligence.css?v=57-live-pulse', html)

    def test_context_chapter_contains_primary_market_news_and_agenda(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        home = html.split('<section id="vestraIntelligenceHome"', 1)[1].split('<div class="vi-back-to-intelligence">', 1)[0]
        self.assertEqual(home.count('class="vi-context-chapter"'), 1)
        self.assertLess(home.index('class="vi-context-chapter"'), home.index('class="vi-priorities"'))
        self.assertEqual(home.count('class="vi-canonical-sections"'), 1)

    def test_observed_concentration_is_not_a_risk_alert(self):
        js = (ROOT / "vestra-intelligence-home.js").read_text(encoding="utf-8")
        self.assertIn("snapshot.top3 * 100", js)
        self.assertIn("análise, não alerta", js)
        self.assertIn("'Sem alertas confirmados · explorar Carteira e Mercado'", js)
        self.assertIn("cards[1].hidden = false", js)
        self.assertIn("cards[2].hidden = !decisionAlert", js)

    def test_current_alert_outranks_exploratory_actions(self):
        js = (ROOT / "vestra-intelligence-home.js").read_text(encoding="utf-8")
        self.assertIn("if (decisionAlert) container.prepend(cards[2]);", js)
        self.assertIn("container.append(cards[0], cards[1], cards[2]);", js)
        self.assertIn("String(index + 1).padStart(2, '0')", js)
        self.assertIn("Verifica a cobertura e o diagnóstico antes de agir.", js)

    def test_canonical_prebreakout_research_does_not_promote_watchlist(self):
        js = (ROOT / "vestra-intelligence-home.js").read_text(encoding="utf-8")
        self.assertIn("updateResearchFocus(hasCanonicalFocus ? canonicalPick : null, stamp);", js)
        self.assertIn("Sem candidato canónico válido nesta leitura", js)
        self.assertIn("não é breakout confirmado nem recomendação.", js)
        self.assertIn("card.removeAttribute('data-vestra-ticker')", js)

    def test_news_can_hydrate_without_legacy_dashboard(self):
        js = (ROOT / "vestra-intelligence-home.js").read_text(encoding="utf-8")
        self.assertIn("fetch('./data/dashboard-news.json'", js)
        self.assertIn("Date.parse(feed?.generated_at)", js)
        self.assertIn("list.dataset.publishedFeed='true'", js)
        self.assertIn("void loadPublishedNews(host);", js)

    def test_portfolio_and_barometer_own_their_metrics(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "vestra-intelligence-home.js").read_text(encoding="utf-8")
        self.assertEqual(html.count('class="vi-live-pulse"'), 1)
        self.assertLess(html.index('data-vi-wealth'), html.index('data-vi-income-monthly'))
        self.assertLess(html.index('data-vi-canonical-score'), html.index('data-vi-pulse-cnn'))
        self.assertLess(html.index('data-vi-pulse-cnn'), html.index('data-vi-canonical-news-list'))
        self.assertIn("'kpiPassiveMonthly'", js)
        self.assertIn("if (income) income.textContent = '••• €'", js)

    def test_published_weekly_events_never_reuse_past_dates(self):
        js = (ROOT / "vestra-intelligence-home.js").read_text(encoding="utf-8")
        self.assertIn("fetch('./data/earnings-latest.json'", js)
        self.assertIn("day >= start && day < end", js)
        self.assertIn("void loadPublishedWeeklyEvents(host);", js)

    def test_editorial_privacy_uses_canonical_controller(self):
        js = (ROOT / "vestra-intelligence-home.js").read_text(encoding="utf-8")
        self.assertIn("typeof window.toggleDashboardPrivacy === 'function'", js)
        self.assertIn("window.toggleDashboardPrivacy();", js)
        self.assertIn("dataset.valuesHidden === 'true'", js)
        self.assertNotIn("getElementById('btnDashboardPrivacy')?.click()", js)

    def test_market_regime_deduplicated_for_mobile(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('class="vi-regime vi-regime-source-detail"', html)
        self.assertIn('class="vi-regime-grid" hidden aria-hidden="true"', html)
        self.assertIn('data-vestra-market-status', html)
        self.assertIn('Explorar a seguir', html)
        js = (ROOT / 'vestra-intelligence-home.js').read_text(encoding='utf-8')
        self.assertIn("'kpiPassiveMonthly2'", js)
        self.assertIn("'portfolioMonthlyValue'", js)

    def test_monthly_income_is_canonical_and_labeled_estimate(self):
        app = (ROOT / "app.js").read_text(encoding="utf-8")
        home = (ROOT / "vestra-intelligence-home.js").read_text(encoding="utf-8")
        self.assertIn("passiveMonthlyEstimate: getDisplayedPassiveAnnual(t) / 12", app)
        self.assertIn("totals?.passiveMonthlyEstimate", home)
        self.assertIn(" / mês · estimado", home)

    def test_unified_sidebar_and_cache_generation(self):
        nav = (ROOT / "vestra-navigation-v2.css").read_text(encoding="utf-8")
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('.sidebar{background:#0d2523!important', nav)
        self.assertIn('vestra-navigation-v2.css?v=7-iphone-density', html)
        self.assertIn('vestra-intelligence.css?v=57-live-pulse', html)
        self.assertRegex(html, r'vestra-intelligence-home\.js\?v=(?:34|[3-9][0-9])')

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

    def test_patimonial_history_is_progressive_and_navigable(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "app.js").read_text(encoding="utf-8")
        css = (ROOT / "vestra-intelligence.css").read_text(encoding="utf-8")
        self.assertIn('id="v2-history-disclosure" open', html)
        self.assertIn('<summary id="v2-history-chapter"', html)
        self.assertIn('id="trendChart"', html)
        self.assertIn('id="snapshotTable"', html)
        self.assertIn('wireDetailHistoryDisclosure', js)
        intel = (ROOT / 'vestra-intelligence-home.js').read_text(encoding='utf-8')
        self.assertIn('historyDisclosure.open = false', intel)
        self.assertIn('trendChart.resize()', js)
        self.assertIn('.v2-detail-history > summary:focus-visible', css)

    def test_detail_tools_compact_responsive_layout(self):
        css = (ROOT / "vestra-intelligence.css").read_text(encoding="utf-8")
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('grid-template-columns:minmax(0,1fr) auto', css)
        self.assertIn('grid-template-columns:minmax(0,1fr)}', css)
        self.assertIn('id="btnToggleDashSecondary"', html)
        self.assertIn('id="dashboardQuickRecordsCard"', html)
        self.assertIn('id="v2-tools-chapter"', html)

    def test_wealth_warning_and_kpi_evidence_layout(self):
        css = (ROOT / "vestra-intelligence.css").read_text(encoding="utf-8")
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn(':is(#negReturnAlert,#riskAlertCard)', css)
        self.assertIn('.kpi-quick__grid{', css)
        self.assertIn('grid-template-columns:repeat(4,minmax(0,1fr))', css)
        self.assertIn('id="riskAlertCard"', html)
        self.assertIn('id="kpiYield"', html)
        self.assertIn('id="kpiPassiveMonthly2"', html)

    def test_decision_triptych_keeps_three_real_actions(self):
        css = (ROOT / "vestra-intelligence.css").read_text(encoding="utf-8")
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        home = html.split('<section id="vestraIntelligenceHome"', 1)[1].split('<div class="vi-back-to-intelligence">', 1)[0]
        self.assertIn('grid-template-columns:repeat(3,minmax(0,1fr))!important', css)
        self.assertIn('@media(max-width:600px)', css)
        self.assertEqual(home.count('class="vi-card vi-action"'), 3)
        self.assertIn('data-vestra-portfolio-evidence', home)
        self.assertIn('data-vestra-decision-state', home)

    def test_mobile_editorial_density_preserves_decision_evidence(self):
        css = (ROOT / "vestra-intelligence.css").read_text(encoding="utf-8")
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('Home iPhone: compress editorial chrome', css)
        self.assertIn('.vi-priorities .vi-action{min-height:62px!important', css)
        self.assertIn('min-height:62px', css)
        home = html.split('<section id="vestraIntelligenceHome"', 1)[1].split('<div class="vi-back-to-intelligence">', 1)[0]
        self.assertEqual(home.count('class="vi-card vi-action"'), 3)
        self.assertIn('data-vestra-decision-state', home)

    def test_market_research_hero_keeps_search_primary(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        css = (ROOT / "vestra-market-surfaces-v2.css").read_text(encoding="utf-8")
        market = html.split('id="viewMarket"', 1)[1]
        self.assertLess(market.index('class="market-hero-simple"'), market.index('class="market-search"'))
        self.assertIn('id="marketSearch"', market)
        self.assertIn('.market-hero-simple h2', css)
        self.assertIn('vestra-market-surfaces-v2.css?v=13-iphone-density', html)

    def test_patrimonial_light_cards_own_safari_text_contrast(self):
        css = (ROOT / "vestra-intelligence.css").read_text(encoding="utf-8")
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        for owner in ("#portfolioQualityCard", "#debtRatioCard", "#maturityAlertsCard", "#btnEnableNotifications"):
            self.assertIn(owner, css)
        self.assertIn("-webkit-text-fill-color:#1c3439!important", css)
        self.assertIn("-webkit-text-fill-color:#526970!important", css)
        self.assertIn('vestra-intelligence.css?v=57-live-pulse', html)

    def test_patrimonial_chapters_share_editorial_type_scale(self):
        css = (ROOT / "vestra-intelligence.css").read_text(encoding="utf-8")
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        for owner in ("#v2-wealth-chapter h2", "#v2-history-chapter>strong",
                      "#v2-tools-chapter .v2-home-secondary-hub__intro h3"):
            self.assertIn(owner, css)
        self.assertIn("--v2-chapter-title-size:clamp(26px,5.7vw,34px)", css)
        self.assertIn("font-size:var(--v2-chapter-title-size)!important", css)
        self.assertIn("-webkit-text-fill-color:#19363b!important", css)
        self.assertIn("-webkit-text-fill-color:#f4f0e7!important", css)
        self.assertIn("vestra-intelligence.css?v=57-live-pulse", html)

    def test_dark_editorial_heading_owners_are_explicit(self):
        css = (ROOT / "vestra-intelligence.css").read_text(encoding="utf-8")
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('Contrast owner for the dark editorial chapter headers', css)
        for selector in ('.v2-home-section-label', '.vi-daily-heading', '.vi-context-heading'):
            self.assertIn(selector, css)
        self.assertIn('-webkit-text-fill-color:#f4f0e8!important', css)
        self.assertIn('vestra-intelligence.css?v=57-live-pulse', html)

    def test_quality_card_generated_labels_own_readable_ink(self):
        css = (ROOT / "vestra-intelligence.css").read_text(encoding="utf-8")
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('#portfolioQualityContent{', css)
        self.assertIn('-webkit-text-fill-color:#213b42!important', css)
        self.assertIn('#portfolioQualityContent [style*="color:"]', css)
        self.assertIn('-webkit-text-fill-color:currentColor!important', css)
        self.assertIn('vestra-intelligence.css?v=57-live-pulse', html)

    def test_health_and_maturity_dynamic_light_card_ink(self):
        css = (ROOT / "vestra-intelligence.css").read_text(encoding="utf-8")
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('#debtRatioContent .health-metric-card', css)
        self.assertIn('--card2:#f8faf7;--muted:#556e73;--line:#cbd6d1', css)
        self.assertIn('#maturityAlertsContent>div', css)
        self.assertIn('-webkit-text-fill-color:currentColor!important', css)
        self.assertIn('vestra-intelligence.css?v=57-live-pulse', html)

    def test_light_health_and_maturity_panels_have_owned_ink(self):
        css = (ROOT / "vestra-intelligence.css").read_text(encoding="utf-8")
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn(":is(#debtRatioContent,#maturityAlertsContent)", css)
        self.assertIn("--card2:#f8faf7;--muted:#556e73;--line:#cbd6d1", css)
        self.assertIn("#debtRatioContent .health-metric-card", css)
        self.assertIn("-webkit-text-fill-color:currentColor!important", css)
        self.assertIn("vestra-intelligence.css?v=57-live-pulse", html)

    def test_mobile_wealth_density_preserves_real_card_owners(self):
        css = (ROOT / "vestra-intelligence.css").read_text(encoding="utf-8")
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("V2.0 iPhone patrimonial reading rhythm", css)
        for selector in ("#v2-wealth-chapter", ".v2-detail-history>summary",
                         ".kpi-quick__cell", "#debtRatioCard", "#maturityAlertsCard"):
            self.assertIn(selector, css)
        self.assertIn("min-height:44px", css)
        self.assertIn("vestra-intelligence.css?v=57-live-pulse", html)

    def test_editorial_iphone_readability_does_not_shrink_evidence(self):
        css = (ROOT / "vestra-intelligence.css").read_text(encoding="utf-8")
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("Vestra 2.0 / iPhone editorial readability", css)
        self.assertIn(".vi-opening .vi-deck{font-size:13px!important", css)
        self.assertIn(".vi-priorities .vi-action small{font-size:12px!important", css)
        self.assertIn(".vi-priorities .vi-action{min-height:64px!important", css)
        self.assertIn("vestra-intelligence.css?v=57-live-pulse", html)

    def test_mobile_context_is_editorial_not_boxed_dashboard(self):
        css = (ROOT / "vestra-intelligence.css").read_text(encoding="utf-8")
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("Vestra 2.0 / editorial Home context", css)
        self.assertIn("display:block!important;border:0!important;border-radius:0!important", css)
        self.assertIn("border-top:1px solid #34514a!important", css)
        self.assertIn("border-left:0!important", css)
        self.assertIn("vestra-intelligence.css?v=57-live-pulse", html)

    def test_desktop_home_editorial_spread_preserves_decision_owners(self):
        css = (ROOT / "vestra-intelligence.css").read_text(encoding="utf-8")
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("V2.0 editorial desktop spread", css)
        self.assertIn("grid-template-columns:minmax(0,1.6fr) minmax(270px,.75fr)", css)
        self.assertIn(".vi-opening .vi-wealth", css)
        self.assertIn(".vi-priorities", css)
        self.assertIn("vestra-intelligence.css?v=57-live-pulse", html)

    def test_editorial_home_medium_width_has_deliberate_bridge(self):
        css = (ROOT / "vestra-intelligence.css").read_text(encoding="utf-8")
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("V2.0 Home / medium-width editorial bridge", css)
        self.assertIn("@media(min-width:601px) and (max-width:1099px)", css)
        self.assertIn("grid-template-columns:minmax(0,1.4fr) minmax(220px,.8fr)", css)
        self.assertIn(".vi-priorities .vi-decisions", css)
        self.assertIn("vestra-intelligence.css?v=57-live-pulse", html)

    def test_small_tablet_home_prevents_editorial_squeeze(self):
        css = (ROOT / "vestra-intelligence.css").read_text(encoding="utf-8")
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("Small tablet bridge: 601–740px", css)
        self.assertIn("@media(min-width:601px) and (max-width:740px)", css)
        self.assertIn("grid-row:auto!important", css)
        self.assertIn("vestra-intelligence.css?v=57-live-pulse", html)

    def test_wealth_dark_heading_and_ivory_tool_cards_have_separate_ink(self):
        css = (ROOT / "vestra-home-density-v2.css").read_text(encoding="utf-8")
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("explicit heading contrast ownership", css)
        for marker in ("#v2-wealth-chapter h2", "#portfolioSourcesCard", "#goalCard", "#milestonesCard"):
            self.assertIn(marker, css)
        self.assertIn("-webkit-text-fill-color:#19363b!important", css)
        self.assertIn("-webkit-text-fill-color:#f4f0e7!important", css)
        self.assertIn("vestra-home-density-v2.css?v=9", html)

    def test_context_and_quick_records_own_safari_ink(self):
        css = (ROOT / "vestra-home-density-v2.css").read_text(encoding="utf-8")
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("Surface-owned ink: context is on dark background", css)
        self.assertIn("#dashboardQuickRecordsCard .card__title", css)
        self.assertIn(":is(.vi-context-heading,.v2-home-section-label)", css)
        self.assertIn("vestra-home-density-v2.css?v=9", html)

if __name__ == "__main__":
    unittest.main()
