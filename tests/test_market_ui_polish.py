from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MarketUiPolishContractTests(unittest.TestCase):
    def test_top_market_identity_row_does_not_repeat_analysis_metrics(self):
        market = (ROOT / 'market.js').read_text(encoding='utf-8')
        detail = market.split('function detailBase(s)', 1)[1].split('function renderDetailTab', 1)[0]
        row = detail.split('<div class="market-dossier-price-row">', 1)[1].split('${dossierScoreBoard(s)}', 1)[0]
        self.assertIn('PREÇO', row)
        self.assertIn('MARKET CAP', row)
        for token in ('FORWARD P/E', 'ROE', 'RECEITA YOY', 'FCF YIELD'):
            self.assertNotIn(token, row)


    def test_score_evidence_layer_keeps_model_specific_quality_not_duplicate_global_metrics(self):
        market = (ROOT / 'market.js').read_text(encoding='utf-8')
        block = market.split('function scoreEvidenceExplanation(s)', 1)[1].split('function scoreWeightExplanation(s)', 1)[0]
        self.assertNotIn('Cobertura global', block)
        self.assertNotIn('confiança da evidência ${Math.round(conf)', block)
        self.assertIn('Métricas críticas', block)
        self.assertIn('Cobertura nativa do modelo', block)
        self.assertIn('Fiabilidade do Score', block)

    def test_published_score_explanation_does_not_repeat_evidence_summary_strip(self):
        market = (ROOT / 'market.js').read_text(encoding='utf-8')
        block = market.split('function scoreExplanation(s)', 1)[1].split('function shortDate(v)', 1)[0]
        published = block.split("if(score==null)", 1)[1].split('return `<div class="market-detail-card market-score-explain">', 1)[1]
        self.assertNotIn('<div class="market-action-context"><span>Cobertura', published)
        self.assertIn('2 · Qualidade da evidência.', published)
        self.assertIn('scoreEvidenceExplanation(s)', published)

    def test_detailed_pillar_metrics_do_not_repeat_top_level_percentiles_or_bars(self):
        market = (ROOT / 'market.js').read_text(encoding='utf-8')
        block = market.split('function dimRows(s)', 1)[1].split('function scoreModelLabel', 1)[0]
        self.assertIn('pillarMetricSummary(s,k)', block)
        self.assertIn('market-dim--evidence-only', block)
        self.assertNotIn('Math.round(v)', block)
        self.assertNotIn('market-bar', block)

    def test_score_explanation_does_not_repeat_top_level_score_or_rank_extremes(self):
        market = (ROOT / 'market.js').read_text(encoding='utf-8')
        block = market.split('function scoreExplanation(s)', 1)[1].split('function shortDate(v)', 1)[0]
        self.assertIn('Como se forma a avaliação', block)
        self.assertIn('DETALHE QUANTITATIVO DOS PILARES', block)
        self.assertNotIn('A puxar para cima:', block)
        self.assertNotIn('A limitar a avaliação:', block)
        self.assertNotIn('${Math.round(score)}/100', block)

    def test_dead_catalyst_wrapper_stays_removed(self):
        market = (ROOT / 'market.js').read_text(encoding='utf-8')
        self.assertNotIn('function catalystPanel(s)', market)
        self.assertIn('window.VestraMarketDossierSignals?.create', market)
        self.assertIn('dossierCatalystsRisks(s)', market)

    def test_dead_congress_wrappers_stay_removed(self):
        market = (ROOT / 'market.js').read_text(encoding='utf-8')
        for name in ('normalizeCongressLive', 'politiciansSnapshotFresh', 'attachCongressToStocks'):
            self.assertNotIn(f'function {name}(', market)
        self.assertIn("async function loadCongressLive(ticker='')", market)
        self.assertIn('congressLiveFeed?.load(ticker)', market)

    def test_additional_dead_market_helpers_stay_removed(self):
        market = (ROOT / 'market.js').read_text(encoding='utf-8')
        for name in ('refreshActiveTabFromLive', 'sparkSvg', 'bestStocks', 'wireVisibleRails', 'wireHorizontalRail'):
            self.assertNotIn(f'function {name}(', market)
        self.assertIn('function resetDossierViewport()', market)
        self.assertIn('window.VestraMarket={ensureLoaded,openTicker,openPortfolioAsset,resolvePortfolioStock,upsertRemoteStock,toggleWatch}', market)

    def test_dead_dossier_helpers_stay_removed(self):
        market = (ROOT / 'market.js').read_text(encoding='utf-8')
        self.assertNotIn('function marketSearchMatches(', market)
        self.assertNotIn('function scrollDossierTop(', market)
        self.assertIn('function renderSearchSuggestions()', market)
        self.assertIn('function resetDossierViewport()', market)

    def test_dead_vestra_read_summary_is_removed(self):
        market = (ROOT / 'market.js').read_text(encoding='utf-8')
        self.assertNotIn('function vestraRead(s)', market)
        self.assertNotIn('Leitura Vestra', market)

    def test_score_breakdown_top_level_keeps_pillars_not_duplicate_base_metrics(self):
        market = (ROOT / 'market.js').read_text(encoding='utf-8')
        block = market.split('function dossierPillarCards(s)', 1)[1].split('function smartMoneyEventType', 1)[0]
        self.assertIn('SCORE BREAKDOWN', block)
        self.assertIn('dossierPillarBand', block)
        self.assertIn('detalhe quantitativo fica nas tabs', block)
        self.assertNotIn('pillarMetricSummary(s,label)', block)
        self.assertNotIn('market-dim__evidence', block)
        score_explanation = market.split('function scoreExplanation(s)', 1)[1].split('function shortDate(v)', 1)[0]
        self.assertIn('DETALHE QUANTITATIVO DOS PILARES', score_explanation)
        self.assertIn('dimRows(s)', score_explanation)


    def test_growth_profile_top_level_is_editorial_summary_not_duplicate_metrics(self):
        market = (ROOT / 'market.js').read_text(encoding='utf-8')
        block = market.split('function dossierGrowthProfile(s)', 1)[1].split('function dossierExpectationsContext(s)', 1)[0]
        self.assertIn('GROWTH PROFILE', block)
        self.assertIn('tab Growth', block)
        self.assertIn('growth_pct', block)
        self.assertNotIn('market-dossier-growth-grid', block)
        self.assertNotIn('EPS YoY', block)
        self.assertNotIn('Margem operacional', block)
        self.assertNotIn('FCF margin', block)
        self.assertNotIn('estimate_momentum_score', block)


    def test_smart_money_top_level_is_editorial_summary_not_duplicate_metrics(self):
        market = (ROOT / 'market.js').read_text(encoding='utf-8')
        block = market.split('function dossierSmartMoney(s)', 1)[1].split('function detailBase(s)', 1)[0]
        self.assertIn('SMART MONEY MAP', block)
        self.assertIn('tab Smart money', block)
        self.assertNotIn('market-dossier-smart-grid', block)
        self.assertNotIn('Compras insider · 30d', block)
        self.assertNotIn('Vendas insider · 30d', block)
        self.assertNotIn('Trades Congresso', block)


    def test_market_expectations_top_level_is_summary_not_duplicate_grid(self):
        market = (ROOT / 'market.js').read_text(encoding='utf-8')
        block = market.split('function dossierExpectationsContext(s)', 1)[1].split('function dossierCatalystsRisks(s)', 1)[0]
        self.assertIn('O que o mercado está a descontar', block)
        self.assertIn('tab Perspetiva', block)
        self.assertIn('tab Valuation', block)
        self.assertNotIn('market-dossier-expectations-grid', block)
        self.assertNotIn('Revisões EPS · 30d', block)
        self.assertNotIn('Target analistas', block)
        self.assertNotIn('Fair value Vestra', block)


    def test_financial_snapshot_top_level_keeps_only_scale_and_profit(self):
        market = (ROOT / 'market.js').read_text(encoding='utf-8')
        block = market.split('function dossierFinancialSnapshot(s)', 1)[1].split('function dossierGrowthProfile(s)', 1)[0]
        for token in ("['Receitas'", "['Lucro líquido'"):
            self.assertIn(token, block)
        for token in ("['Free cash flow'", "['Cash flow operacional'", "['Caixa líquido / dívida'", "['Debt / Equity'", "['Current ratio'", "['Margem líquida'"):
            self.assertNotIn(token, block)
        self.assertIn('tab Financeiro', block)


    def test_overview_does_not_repeat_score_pillars_or_risks(self):
        market = (ROOT / 'market.js').read_text(encoding='utf-8')
        overview = market.split("if(tab==='overview')", 1)[1].split("if(tab==='perspective')", 1)[0]
        self.assertNotIn('Ver pilares e detalhe quantitativo', overview)
        self.assertNotIn('Pilares · percentis relativos', overview)
        self.assertNotIn('Riscos adicionais', overview)
        self.assertIn('${scoreExplanation(s)}', overview)



    def test_score_history_is_compact_when_no_real_series_exists(self):
        market = (ROOT / 'market.js').read_text(encoding='utf-8')
        css = (ROOT / 'market.css').read_text(encoding='utf-8')
        scoreboard = market.split('function dossierScoreBoard(s)', 1)[1].split('function dossierFullPicture(s)', 1)[0]
        self.assertIn("const historyClass=historyHtml?' market-dossier-scoreboard--with-history':'';", scoreboard)
        self.assertNotIn('A série histórica ainda não está disponível para este ativo.', scoreboard)
        self.assertNotIn('market-dossier-score-history--empty', scoreboard)
        self.assertIn('.market-dossier-scoreboard--with-history{grid-template-columns:minmax(150px,220px) minmax(220px,1fr)}', css)


    def test_editorial_dossier_avoids_repeated_top_level_metrics(self):
        market = (ROOT / 'market.js').read_text(encoding='utf-8')
        scoreboard = market.split('function dossierScoreBoard(s)', 1)[1].split('function dossierFullPicture(s)', 1)[0]
        snapshot = market.split('function dossierFinancialSnapshot(s)', 1)[1].split('function dossierGrowthProfile(s)', 1)[0]
        growth = market.split('function dossierGrowthProfile(s)', 1)[1].split('function dossierExpectationsContext(s)', 1)[0]
        overview = market.split("if(tab==='overview')", 1)[1].split("if(tab==='perspective')", 1)[0]
        self.assertNotIn('market-dossier-pillars', scoreboard)
        self.assertNotIn("['ROE'", snapshot)
        self.assertNotIn("['Margem operacional'", snapshot)
        self.assertNotIn("['Receita YoY'", growth)
        self.assertIn('${evidencePanel(s)}', overview)
        self.assertNotIn('${catalystPanel(s)}', overview)



    def test_editorial_dossier_surfaces_compact_catalysts_and_risks(self):
        market = (ROOT / 'market.js').read_text(encoding='utf-8')
        block = market.split('function dossierCatalystsRisks(s)', 1)[1].split('function dossierPillarBand', 1)[0]
        self.assertIn('CATALYSTS & RISKS', block)
        self.assertIn('O que pode mudar a tese', block)
        self.assertIn('Investment Case', block)
        for token in ('catalyst_events', 'thesis_evolution_drivers', 'earnings_intelligence_drivers', 'thesis_risks'):
            self.assertIn(token, block)
        self.assertNotIn('market-dossier-catalyst-grid', block)
        self.assertNotIn('<ul>', block)


    def test_editorial_dossier_includes_financial_snapshot(self):
        market = (ROOT / 'market.js').read_text(encoding='utf-8')
        css = (ROOT / 'market.css').read_text(encoding='utf-8')
        self.assertIn('function dossierFinancialSnapshot(s)', market)
        self.assertIn('FINANCIAL SNAPSHOT', market)
        self.assertIn('Escala do negócio', market)
        for token in ('free_cash_flow', 'operating_cash_flow', 'net_cash', 'operating_margin', 'profit_margin', 'roe'):
            self.assertIn(token, market)
        self.assertIn('market-dossier-financial-grid', css)
        self.assertIn('grid-template-columns:repeat(2,minmax(0,1fr))', css)



    def test_investment_case_valuation_is_editorial_not_duplicate_numbers(self):
        market = (ROOT / 'market.js').read_text(encoding='utf-8')
        block = market.split('function investmentCase(s)', 1)[1].split('function dossierScoreHistory', 1)[0]
        self.assertIn('Está caro ou barato?', block)
        self.assertIn('tab Valuation', block)
        self.assertIn('Abaixo do fair value', block)
        self.assertNotIn('fair_value_upside_pct', block)
        self.assertNotIn('money(s.fair_value_low', block)
        self.assertNotIn('Math.abs(valuationDelta)', block)

    def test_investment_case_why_fallback_does_not_repeat_thesis_summary(self):
        market = (ROOT / 'market.js').read_text(encoding='utf-8')
        block = market.split('function investmentCase(s)', 1)[1].split('function dossierScoreHistory', 1)[0]
        self.assertIn("Sem evidência específica adicional para além da síntese da tese.", block)
        self.assertNotIn("const why=evidence.length?evidence.slice(0,3):[s.thesis_summary", block)

    def test_investment_case_watchpoints_do_not_repeat_market_expectations_direction(self):
        market = (ROOT / 'market.js').read_text(encoding='utf-8')
        block = market.split('function investmentCase(s)', 1)[1].split('function dossierScoreHistory', 1)[0]
        self.assertNotIn("watch.push('Expectativas a melhorar')", block)
        self.assertNotIn("watch.push('Expectativas a piorar')", block)
        self.assertIn("watch.push('Tese quantitativa a melhorar')", block)
        self.assertIn("watch.push('Tese quantitativa a piorar')", block)

    def test_investment_case_watchpoints_do_not_repeat_detailed_market_metrics(self):
        market = (ROOT / 'market.js').read_text(encoding='utf-8')
        block = market.split('function investmentCase(s)', 1)[1].split('function dossierScoreHistory', 1)[0]
        self.assertNotIn('Próximo evento ·', block)
        self.assertIn('Tese quantitativa a melhorar', block)
        self.assertNotIn('Revisões EPS ·', block)
        self.assertNotIn('Target consenso ·', block)
        self.assertNotIn('Insiders 30d ·', block)
        self.assertNotIn('estimate_momentum_score', block)


    def test_full_picture_business_description_is_separate_from_investment_thesis(self):
        market = (ROOT / 'market.js').read_text(encoding='utf-8')
        full_picture = market.split('function dossierFullPicture(s)', 1)[1].split('function dossierFinancialSnapshot(s)', 1)[0]
        investment = market.split('function investmentCase(s)', 1)[1].split('function dossierScoreHistory(s)', 1)[0]
        self.assertIn('long_business_summary', full_picture)
        self.assertIn('business_summary', full_picture)
        self.assertNotIn('thesis_summary', full_picture)
        self.assertIn('thesis_summary', investment)
        self.assertNotIn('s.business_summary', investment)


    def test_editorial_dossier_includes_company_identity_facts(self):
        market = (ROOT / 'market.js').read_text(encoding='utf-8')
        css = (ROOT / 'market.css').read_text(encoding='utf-8')
        self.assertIn('Ficha da empresa', market)
        for token in ("['Indústria',industry]", "['País / região',geography]", "['Tipo',quoteType]", "['Moeda'"):
            self.assertIn(token, market)
        full_picture = market.split('function dossierFullPicture(s)', 1)[1].split('function dossierFinancialSnapshot(s)', 1)[0]
        for duplicate in ("['Setor'", "['Bolsa'", "['Market cap'"):
            self.assertNotIn(duplicate, full_picture)
        self.assertIn('market-dossier-company-facts', css)
        self.assertIn('grid-template-columns:repeat(4,minmax(0,1fr))', css)




    def test_smart_money_tab_maps_declared_events_without_invented_performance(self):
        market = (ROOT / 'market.js').read_text(encoding='utf-8')
        css = (ROOT / 'market.css').read_text(encoding='utf-8')
        self.assertIn('function smartMoneyTimeline(s)', market)
        self.assertIn('Preço e operações declaradas', market)
        self.assertIn('price_history_1y', market)
        self.assertIn('transaction_date', market)
        self.assertIn('Não calculamos retorno pós-operação nem taxa de acerto', market)
        self.assertIn('market-smart-marker--insider', css)
        self.assertIn('market-smart-marker--congress', css)


    def test_editorial_dossier_keeps_expectations_detail_in_perspective_data(self):
        market = (ROOT / 'market.js').read_text(encoding='utf-8')
        block = market.split('function dossierExpectationsContext(s)', 1)[1].split('function dossierCatalystsRisks(s)', 1)[0]
        self.assertIn('function dossierExpectationsContext(s)', market)
        self.assertIn('MARKET EXPECTATIONS', market)
        self.assertIn('O que o mercado está a descontar', market)
        self.assertIn('tab Perspetiva', block)
        self.assertIn('tab Valuation', block)
        for token in ('analyst_eps_revisions_up_30d', 'estimate_momentum_score', 'fair_value_upside_pct'):
            self.assertIn(token, market)
        self.assertNotIn('market-dossier-expectations-grid', block)



    def test_editorial_dossier_has_compact_score_breakdown_cards(self):
        market = (ROOT / 'market.js').read_text(encoding='utf-8')
        css = (ROOT / 'market.css').read_text(encoding='utf-8')
        self.assertIn('function dossierPillarCards(s)', market)
        self.assertIn('SCORE BREAKDOWN', market)
        self.assertIn('Porque tem este Score?', market)
        self.assertIn('pillarMetricSummary(s,label)', market)
        self.assertIn('Os pilares são rankings relativos', market)
        self.assertIn('market-dossier-breakdown-grid', css)
        self.assertIn('grid-template-columns:repeat(2,minmax(0,1fr))', css)



    def test_editorial_company_dossier_hierarchy(self):
        market = (ROOT / 'market.js').read_text(encoding='utf-8')
        css = (ROOT / 'market.css').read_text(encoding='utf-8')
        for token in ('dossierScoreBoard', 'dossierFullPicture', 'dossierGrowthProfile', 'dossierSmartMoney'):
            self.assertIn(token, market)
        self.assertIn('THE FULL PICTURE', market)
        self.assertIn('SMART MONEY MAP', market)
        self.assertIn('GROWTH PROFILE', market)
        self.assertIn('<h1>', market)
        self.assertIn('<h2 class="market-dossier-symbol">', market)
        self.assertIn('market-dossier-scoreboard', css)
        self.assertIn('market-dossier-editorial-card', css)
        self.assertNotIn('market-dossier-score-history--empty', css)
        self.assertNotIn('A série histórica ainda não está disponível', market)
        self.assertIn('data-live-field="current_price"', market)
        price_row = market.split('<div class="market-dossier-price-row">', 1)[1].split('${dossierScoreBoard(s)}', 1)[0]
        for field in ('forward_pe', 'roe', 'revenue_growth', 'fcf_yield'):
            self.assertNotIn(f'data-live-field="{field}"', price_row)


    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / 'market-ui-polish.js').read_text(encoding='utf-8')
        cls.dossier = (ROOT / 'market-dossier-controls.js').read_text(encoding='utf-8')
        cls.dossier_css = (ROOT / 'market-dossier-controls.css').read_text(encoding='utf-8')
        cls.loader = (ROOT / 'market-static-universe.js').read_text(encoding='utf-8')
        cls.analysis_tools = (ROOT / 'market-analysis-tools-runtime.js').read_text(encoding='utf-8')
        cls.analysis_tools_css = (ROOT / 'market-analysis-tools-runtime.css').read_text(encoding='utf-8')

    def test_dossier_geometry_has_one_owner_and_one_fixed_action_group(self):
        self.assertNotIn('right:max(calc(env(safe-area-inset-right) + 68px),68px)!important', self.source)
        self.assertNotIn('#marketSheet .market-close-persistent,', self.source)
        self.assertNotIn('market-detail-actions', self.source)
        self.assertNotIn("document.createElement('style')", self.source)
        self.assertNotIn('style.textContent', self.source)
        self.assertIn("market-dossier-controls.css?v=1.4", self.dossier)
        self.assertNotIn("document.createElement('style')", self.dossier)
        self.assertNotIn('style.textContent', self.dossier)
        self.assertIn('.market-detail-actions{', self.dossier_css)
        self.assertIn('position:fixed!important', self.dossier_css)
        self.assertIn('gap:8px!important', self.dossier_css)
        self.assertIn('> .market-watch--detail{', self.dossier_css)
        self.assertIn('.market-detail-actions .market-close{', self.dossier_css)
        self.assertIn('width:44px!important', self.dossier_css)
        self.assertIn('height:44px!important', self.dossier_css)
        self.assertIn('> .market-close-persistent{', self.dossier_css)
        self.assertIn('display:grid!important', self.dossier_css)
        self.assertIn('visibility:visible!important', self.dossier_css)
        self.assertIn('pointer-events:auto!important', self.dossier_css)
        self.assertIn("version: '1.3'", self.source)
        self.assertIn("version: '2.0'", self.dossier)
        self.assertIn('right:max(calc(env(safe-area-inset-right) + 66px),66px)!important', self.dossier_css)
        self.assertIn('.market-detail-actions .market-close{\n  display:none!important', self.dossier_css)
        self.assertIn('market-dossier-action-portal', self.dossier_css)
        self.assertIn('position:fixed!important', self.dossier_css)
        self.assertIn("PORTAL_ID = 'marketDossierActionPortal'", self.dossier)
        self.assertNotIn('market-dossier-action-portal__identity', self.dossier)
        self.assertIn('syncPortal(sheet)', self.dossier)
        self.assertNotIn('MutationObserver', self.dossier)

    def test_politicians_state_is_cleared_before_normal_market_mode_switch(self):
        self.assertIn("[data-politicians-mode]", self.source)
        self.assertIn("[data-market-mode]", self.source)
        self.assertIn("classList.remove('is-active')", self.source)
        self.assertIn("document.addEventListener('click', onClickCapture, true)", self.source)

    def test_stock_themes_loader_is_bounded_and_retryable(self):
        self.assertIn('const STOCK_THEMES_LOAD_TIMEOUT_MS = 8000', self.source)
        self.assertIn('let stockThemesLoadPromise = null', self.source)
        self.assertIn("script.addEventListener('load', onLoad, { once: true })", self.source)
        self.assertIn("script.addEventListener('error', onError, { once: true })", self.source)
        self.assertIn('timeoutId = setTimeout(fail, STOCK_THEMES_LOAD_TIMEOUT_MS)', self.source)
        self.assertIn('if (script.isConnected) script.remove()', self.source)
        self.assertIn('if (attempt < 1', self.source)
        self.assertIn('setTimeout(() => ensureStockThemesTools(attempt + 1), 1000)', self.source)
        self.assertIn('stockThemesLoadPromise = null', self.source)
        self.assertNotIn("if (window.VestraMarketStockThemesTools || document.querySelector('script[data-vestra-stock-themes-tools]')) return;", self.source)

    def test_no_market_data_or_financial_semantics_changed(self):
        self.assertNotIn('fetch(', self.source)
        self.assertNotIn('score', self.source.lower())
        self.assertNotIn('risk_gate', self.source.lower())
        self.assertNotIn('localStorage', self.source)
        self.assertNotIn('indexedDB', self.source)

    def test_companions_are_reachable_from_loader(self):
        self.assertIn('ensureMarketUiPolish', self.loader)
        self.assertIn('market-ui-polish.js?v=1.3', self.loader)
        self.assertIn('ensureAnalysisToolsRuntime', self.loader)
        self.assertIn('market-analysis-tools-runtime.js?v=1.3', self.loader)
        self.assertIn("version: '1.30'", self.loader)

    def test_analysis_tools_have_searchable_compare_and_news_and_lazy_scanner(self):
        self.assertIn('marketCompareSearch', self.analysis_tools)
        self.assertIn('compareCandidates', self.analysis_tools)
        self.assertIn('marketNewsSearch', self.analysis_tools)
        self.assertIn('newsCandidates', self.analysis_tools)
        self.assertIn('VestraMarketScannerData', self.analysis_tools)
        self.assertIn('data-tool-scanner-strategy', self.analysis_tools)
        self.assertIn('window.VestraNavigation', self.analysis_tools)
        self.assertIn("nav.openCompany(ticker, { origin: 'market' })", self.analysis_tools)
        self.assertNotIn('VestraMarket?.openTicker', self.analysis_tools)
        self.assertIn("market-analysis-tools-runtime.css?v=1.0", self.analysis_tools)
        self.assertNotIn("document.createElement('style')", self.analysis_tools)
        self.assertNotIn('style.textContent', self.analysis_tools)
        self.assertIn('overflow-y:auto', self.analysis_tools_css)
        self.assertIn('.market-tool-runtime__search', self.analysis_tools_css)
        self.assertIn('.market-tool-runtime__chips', self.analysis_tools_css)
        self.assertIn("version:'1.3'", self.analysis_tools)


if __name__ == '__main__':
    unittest.main(verbosity=2)
