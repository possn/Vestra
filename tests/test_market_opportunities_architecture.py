from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


class CanonicalMarketOpportunityTests(unittest.TestCase):
    def test_hotfix_loads_canonical_modules_not_legacy_opportunity_overlays(self):
        hotfix = read('index.html')
        loader = read('market-static-universe.js')
        self.assertNotIn('src="market-opportunities.js', hotfix)
        self.assertNotIn('src="market-opportunity-lenses.js', hotfix)
        self.assertIn("market-opportunities.js?v=1.9", loader)
        self.assertIn("market-opportunity-lenses.js?v=3.1", loader)
        self.assertLess(loader.index("market-opportunities.js?v=1.9"), loader.index("market-opportunity-lenses.js?v=3.1"))
        self.assertNotIn('src="vestra-portfolio-focus.js', hotfix)
        self.assertNotIn("vestra-portfolio-focus.js", loader)
        self.assertNotIn("vestra-ux-v452.js", hotfix)
        self.assertNotIn("vestra-ux-v453.js", hotfix)
        self.assertNotIn("vestra-ux-v454.js", hotfix)

    def test_canonical_opportunity_engine_keeps_v453_contract(self):
        source = read('market-opportunities.js')
        for token in (
            "const LEGACY_FEATURED_OPPORTUNITY_MIN_SCORE=54",
            "function discoveryEligible(s)",
            "if(publishedEligible!==null)return publishedEligible",
            "if(!discoveryEligible(s))return false",
            "publishedScore!=null&&publishedScore>=LEGACY_FEATURED_OPPORTUNITY_MIN_SCORE",
            "sc==null||sc<58||cov==null||cov<55||conf==null||conf<50",
            "return timing(s)>=48 && confirmed(s)>=2",
            "const published=n(s?.opportunity_score)",
            "[n(s?.score),.25]",
            "[timing(s),.29]",
            "[n(s?.recovery_score),.10]",
            "[n(s?.qarp_score),.11]",
            "[n(s?.moat_score),.08]",
            "[n(s?.capital_allocation_intelligence_score),.06]",
            "[n(s?.value_pct),.06]",
            "[n(s?.growth_pct),.02]",
            "[n(s?.sector_native_score),.03]",
            "Math.min(5,confirmed(s)*1.25)",
        ):
            self.assertIn(token, source)

    def test_discovery_eligibility_is_distinct_from_featured_shortlist_threshold(self):
        source = read('market-opportunities.js')
        ranker = read('scripts/opportunity_rank.py')
        discovery = source.split('function discoveryEligible(s){', 1)[1].split('function eligible(s){', 1)[0]
        featured = source.split('function eligible(s){', 1)[1].split('function fallbackUpsideSupport', 1)[0]
        self.assertIn("if(publishedEligible!==null)return publishedEligible", discovery)
        self.assertNotIn('opportunity_score', discovery)
        self.assertIn('LEGACY_FEATURED_OPPORTUNITY_MIN_SCORE=54', source)
        self.assertIn('publishedScore!=null&&publishedScore>=LEGACY_FEATURED_OPPORTUNITY_MIN_SCORE', featured)
        self.assertIn('Discovery elegível e classificado pelo motor', source)
        self.assertIn('“Interessante” ou melhor', source)
        self.assertIn("FEATURED_OPPORTUNITY_MIN_SCORE = 54.0", ranker)
        self.assertIn("elif opp >= FEATURED_OPPORTUNITY_MIN_SCORE:", ranker)
        self.assertIn('label = "Interessante"', ranker)
        
    def test_legacy_low52_surface_reuses_canonical_discovery_instead_of_second_score(self):
        market = read('market.js')
        start = market.index('function low52OpportunityRank')
        end = market.index('function renderLows', start)
        block = market[start:end]
        self.assertIn("if(s?.opportunity_eligible!==true) return null;", block)
        self.assertIn("const score=n(s?.opportunity_score);", block)
        self.assertNotIn("confidence_score", block)
        self.assertNotIn("low52_score", block)
        self.assertNotIn("recovery_score", block)
        self.assertNotIn("risk_gate", block)
        render = market.split('function renderLows(){', 1)[1].split('const ETF_THEMES', 1)[0]
        self.assertIn(".filter(x=>x.opportunityRank!=null)", render)
        self.assertIn("Discovery canónico", render)

    def test_strategy_lenses_cannot_bypass_canonical_discovery_eligibility(self):
        source = read('market-opportunities.js')
        start = source.index("function lensEligible(s,lens){")
        end = source.index("function sleeveScores(s)", start)
        block = source[start:end]
        self.assertIn("if(lens==='all')return eligible(s);", block)
        self.assertIn("if(!discoveryEligible(s))return false;", block)
        self.assertLess(
            block.index("if(!discoveryEligible(s))return false;"),
            block.index("if(lens==='low52')"),
        )

    def test_backend_owns_featured_opportunity_decision(self):
        source = read('market-opportunities.js')
        ranker = read('scripts/opportunity_rank.py')
        self.assertIn('"opportunity_featured": False', ranker)
        self.assertIn('"opportunity_featured": bool(opp is not None and opp >= FEATURED_OPPORTUNITY_MIN_SCORE)', ranker)
        self.assertIn('"opportunity_featured_min_score": FEATURED_OPPORTUNITY_MIN_SCORE', ranker)
        self.assertIn("const publishedFeatured=typeof s?.opportunity_featured==='boolean'?s.opportunity_featured:null", source)
        self.assertIn("if(publishedFeatured!==null)return publishedFeatured", source)
        self.assertIn("LEGACY_FEATURED_OPPORTUNITY_MIN_SCORE=54", source)
        self.assertNotIn("featuredMinScore:", source)

    def test_opportunity_ui_does_not_alias_vestra_score_as_quality(self):
        source = read('market-opportunities.js')
        self.assertIn('Score Vestra ${Math.round(n(s?.score)||0)}', source)
        self.assertIn('prioridade para investigar agora', source)
        self.assertIn('≠ PORTFOLIO FIT', source)
        self.assertIn('adequação à tua carteira só é avaliada na Carteira / Optimizar', source)
        self.assertNotIn('<span>Qualidade ${Math.round(n(s?.score)||0)}</span>', source)

    def test_discovery_score_is_distinct_from_confidence_and_portfolio_fit(self):
        source = read('market-opportunities.js')
        ranker = read('scripts/opportunity_rank.py')
        self.assertIn('function discoveryScore(s)', source)
        self.assertIn('const published=n(s?.opportunity_score)', source)
        self.assertIn('function fallbackUpsideSupport(s)', source)
        self.assertIn("if(support==='negative')x=Math.min(x,49)", source)
        self.assertIn("else if(['weak','unavailable'].includes(support))x=Math.min(x,64)", source)
        self.assertIn("else if(support==='moderate')x=Math.min(x,77)", source)
        self.assertNotIn("else if(pt!=null)x+=Math.max(-5,Math.min(6,pt/7))", source)
        self.assertIn('score:discoveryScore', source)
        self.assertNotIn('[n(s?.confidence_score),.06]', source)
        sleeve_block = ranker.split('sleeve_parts = [', 1)[1].split(']', 1)[0]
        self.assertIn('(strength, .36)', sleeve_block)
        self.assertIn('(asymmetry, .28)', sleeve_block)
        self.assertIn('(inflection, .36)', sleeve_block)
        self.assertNotIn('(conf,', sleeve_block)
        self.assertIn('raw, _ = _fixed_weighted(sleeve_parts)', ranker)
        self.assertIn('_gate("confidence"', ranker)
        self.assertIn('if coverage < 65 or conf < 60:', ranker)
        self.assertIn('Portfolio fit is intentionally absent', ranker)
        self.assertNotIn('portfolio_fit', sleeve_block)
        self.assertIn('<small>DISCOVERY</small>', source)
        self.assertNotIn('<small>ENTRY</small>', source)

    def test_portfolio_fit_is_labeled_only_in_portfolio_context(self):
        source = read('market-opportunities.js')
        market = read('market.js')
        discovery_block = source.split('function discoveryScore(s)', 1)[1].split('function eligible', 1)[0]
        self.assertNotIn('portfolioFit', discovery_block)
        self.assertIn('<small>PORTFOLIO FIT</small><h4>Aderência desta carteira aos objetivos</h4>', market)
        self.assertIn('function portfolioFit(', market)


    def test_portfolio_fit_per_asset_is_explainable_not_a_super_score(self):
        market = read('market.js')
        self.assertIn('function portfolioFitSummary(ctx)', market)
        self.assertIn("Portfolio Fit: ${label}", market)
        self.assertIn("posição ${(n(fit.positionPct)||0).toFixed(1)}%", market)
        self.assertIn("setor ${(n(fit.sectorPct)||0).toFixed(1)}%", market)
        self.assertIn("ETF indireto ${(n(fit.indirectPct)||0).toFixed(1)}%", market)
        self.assertIn("fit.fit==='concentrated'?'Concentrado':fit.fit==='watch'?'Atenção':'Equilibrado'", market)
        self.assertNotIn('portfolioFitScore', market)
        action_block = market.split('function portfolioAction(stock, alternativesByTicker, context)', 1)[1].split('const PORTFOLIO_TARGETS_KEY', 1)[0]
        self.assertIn("ctx.fit==='concentrated'||ctx.fit==='watch'", action_block)
        self.assertIn("key:'hold',label:'Manter'", action_block)
        self.assertIn("key:'reinforce',label:'Reforçar'", action_block)


    def test_portfolio_decision_surfaces_reuse_canonical_portfolio_action(self):
        market = read('market.js')
        intelligence = market.split('function portfolioIntelligence(rows,total)', 1)[1].split('function buildMultiMovePlan', 1)[0]
        center = market.split('function renderPortfolioDecisionCenter(rows,total,etfOptimizeRows=[])', 1)[1].split('function portfolioIntelligence(rows,total)', 1)[0]
        self.assertIn("const reinforce=actionRows.filter(r=>r.action?.key==='reinforce')", intelligence)
        self.assertIn("const review=actionRows.filter(r=>['review','replace'].includes(r.action?.key))", intelligence)
        self.assertIn('renderPortfolioDecisionCenter(actionRows,total,etfOptimizeRows)', intelligence)
        self.assertIn("const reinforce=ranked.filter(r=>r.action?.key==='reinforce')", center)
        self.assertIn("const review=ranked.filter(r=>['review','replace'].includes(r.action?.key))", center)
        self.assertNotIn("const reinforce=ranked.filter(r=>r.conviction!=null&&r.conviction>=70", center)
        self.assertIn('const materialEtfOptimize=', center)
        self.assertIn("kind:'etfoptimize'", center)
        self.assertIn("Comparar ${materialEtfOptimize.source.ticker}", center)
        self.assertIn("if(kind==='etfoptimize'){ scrollTo(document.querySelector('.market-etf-optimize')); return; }", market)


    def test_inflation_shield_is_an_explainable_portfolio_regime_lens(self):
        market = read('market.js')
        css = read('market.css')
        self.assertIn('function inflationShieldProfile(stock)', market)
        self.assertIn('function renderInflationShield(rows,portfolioTotal=0)', market)
        self.assertIn("const partial=portfolioTotal>0&&coverage<35", market)
        self.assertIn("Como reage a parte classificável à inflação?", market)
        self.assertIn("renderInflationShield(ranked,total)", market)
        self.assertIn('INFLATION SHIELD · REGIME LENS', market)
        self.assertIn('Não altera Vestra Score, Discovery nem Portfolio Fit', market)
        self.assertIn('Proxy, não backtest', market)
        self.assertIn('Não são uma shortlist de “melhores hedges”', market)
        self.assertIn('Ver mais ${remaining.length} posições classificadas', market)
        self.assertIn('Como é feita a classificação?', market)
        self.assertIn("bucket:'benefit'", market)
        self.assertIn("bucket:'resilient'", market)
        self.assertIn("'vulnerable'", market)
        self.assertNotIn('inflationShieldScore', market)
        discovery = read('market-opportunities.js')
        self.assertNotIn('inflationShield', discovery)
        self.assertIn('.market-inflation-zones{', css)
        self.assertIn('.market-inflation-bar__benefit', css)
        self.assertIn('@media(max-width:620px)', css)


    def test_opportunities_reuse_canonical_market_universe_without_refetch(self):
        source = read('market-opportunities.js')
        universe = read('market-static-universe.js')
        self.assertIn("window.VestraMarketStaticUniverse", source)
        self.assertIn("getStocks", source)
        self.assertNotIn("fetch('./data/stocks-index.json'", source)
        self.assertNotIn("fetch('./data/stocks.json'", source)
        self.assertIn("function getStocks()", universe)
        self.assertIn("sharedStocks = stocks", universe)
        self.assertIn("window.VestraMarketOpportunities", source)

    def test_strategy_lenses_rank_from_full_universe_not_current_twelve_rows(self):
        source = read('market-opportunities.js')
        lenses = read('market-opportunity-lenses.js')
        market = read('market.js')
        self.assertIn("function rankLens(universe,lens", source)
        self.assertIn(".filter(s=>lensEligible(s,lens))", source)
        self.assertIn("ranked.sort((a,b)=>(discoveryScore(b)||0)-(discoveryScore(a)||0))", source)
        self.assertIn("const rows=rankLens(universe,activeLens,{limit:12,sector:sec})", source)
        self.assertIn("function lensEligible(s,lens)", source)
        self.assertIn("function lensScore(s,lens)", source)
        self.assertIn("above>=-0.5&&above<=5", source)
        self.assertIn("!['confirmed','recovering'].includes(rec)", source)
        self.assertIn("function opportunities(lens=activeLens,sectorOverride='')", source)
        self.assertIn("const sec=t(sectorOverride)||t(active?.dataset.marketSector)||t(section.querySelector('[data-market-sector-select]')?.value)||'all'", source)
        self.assertIn("window.VestraMarketOpportunities?.selectLens?.(activeLens,moreSectorValue())", lenses)
        self.assertIn("function deferNativeSectorCommit(event)", lenses)
        self.assertIn("event.stopImmediatePropagation()", lenses)
        self.assertIn("requestAnimationFrame(()=>requestAnimationFrame(()=>", lenses)
        self.assertIn("document.addEventListener('change',deferNativeSectorCommit,true)", lenses)
        self.assertIn("deferredSectorEvents.add(commit)", lenses)
        self.assertIn("live.dispatchEvent(commit)", lenses)
        self.assertNotIn("window.VestraMarketOpportunities?.refresh?.(activeLens,selected)", lenses)
        self.assertNotIn("refreshAfterSectorSelection", lenses)
        self.assertIn("if(e.target.matches('[data-market-sector-select]') && e.target.value){ M.sector=e.target.value; renderPrimary(); }", market)
        self.assertNotIn("function lensMatch(row, lens)", lenses)
        self.assertNotIn("querySelectorAll('.market-list .market-row')", lenses)

    def test_strategy_lenses_preserve_canonical_discovery_order(self):
        source = read('market-opportunities.js')
        block = source.split('function lensScore(s,lens){', 1)[1].split('function rankedCandidates', 1)[0]
        ranked = source.split('function rankedCandidates(universe,lens,sector=\'all\'){', 1)[1].split('function diversify', 1)[0]
        buckets = source.split("const buckets=archetypes.map(type=>({", 1)[1].split("}));", 1)[0]
        self.assertIn('return discoveryScore(s)||0', block)
        self.assertNotIn('lensTilt', source)
        self.assertNotIn('discovery*.82', source)
        self.assertIn("ranked.sort((a,b)=>(discoveryScore(b)||0)-(discoveryScore(a)||0))", ranked)
        self.assertIn("rows:general.filter(s=>lensEligible(s,type)).sort((a,b)=>(discoveryScore(b)||0)-(discoveryScore(a)||0))", buckets)
        self.assertNotIn('confidence_score', block)

    def test_opportunity_rows_explain_why_now_without_new_alpha(self):
        source = read('market-opportunities.js')
        css = read('market-opportunities.css')
        self.assertIn('function whyNowItems(s)', source)
        self.assertIn('function whyNowHtml(s)', source)
        self.assertIn('Porque agora', source)
        for token in ('opportunity_valuation_evidence', 'opportunity_revision_evidence', 'opportunity_market_regime', 'opportunity_rotation_signal', 'opportunity_event_risk'):
            self.assertIn(token, source)
        self.assertIn("items.push({kind:'risk',label:'Risco principal'", source)
        self.assertIn('return items.slice(0,4)', source)
        self.assertIn('.ux453-why{', css)
        self.assertIn('.ux453-why__row{', css)
        self.assertIn('@media(max-width:620px)', css)
        why_block = source.split('function whyNowItems(s){', 1)[1].split('function whyNowHtml', 1)[0]
        self.assertNotIn('discoveryScore(', why_block)
        self.assertNotIn('lensScore(', why_block)

    def test_opportunity_cards_keep_metrics_beside_why_now_on_mobile(self):
        source = read('market-opportunities.js')
        css = read('market-opportunities.css')
        self.assertIn('ux453-detail-grid', source)
        self.assertIn('ux453-card-metrics', source)
        self.assertIn('.ux453-detail-grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(112px,.34fr)', css)
        self.assertIn('@media(max-width:620px)', css)
        self.assertIn('.ux453-detail-grid{grid-template-columns:minmax(0,1fr) 108px', css)

    def test_opportunity_rows_explain_driver_and_company_vs_setup(self):
        source = read('market-opportunities.js')
        css = read('market-opportunities.css')
        for token in ('function sleeveScores(s)', 'function dominantSleeve(s)', 'function opportunityType(s)', 'Força', 'Assimetria', 'Inflection'):
            self.assertIn(token, source)
        self.assertIn('boa empresa; timing ainda incompleto', source)
        self.assertIn('setup forte; qualidade estrutural a confirmar', source)
        self.assertIn('qualidade + oportunidade agora', source)
        self.assertIn('is-driver', source)
        self.assertIn('.ux453-sleeves span.is-driver', css)
        self.assertIn('function sleeveCoverage(s)', source)
        self.assertIn('function credibleDominantSleeve(s)', source)
        self.assertIn("cov==null||cov>=70?dom:null", source)
        self.assertIn('evidência limitada', source)
        self.assertIn('dom=credibleDominantSleeve(s)', source)
        self.assertIn('function discoveryCaps(s)', source)
        self.assertIn('function capSummary(s)', source)
        self.assertIn('Limitado:', source)
        self.assertIn('ux453-cap-note', source)
        self.assertIn('.ux453-cap-note{', css)

    def test_general_and_strategy_lenses_keep_distinct_eligibility_contracts(self):
        source = read('market-opportunities.js')
        self.assertIn("if(lens!=='all')return rankedCandidates(universe,lens,sector).slice(0,limit)", source)
        self.assertIn("const canonical=(Array.isArray(universe)?universe:[]).filter(s=>eligible(s))", source)
        self.assertIn("if(lens==='low52')", source)
        self.assertIn("coreCandidate(s,{scoreMin:50,coverageMin:45,confidenceMin:45,criticalMin:25})", source)

    def test_general_shortlist_never_uses_looser_lens_eligibility_to_fill_slots(self):
        source = read('market-opportunities.js')
        block = source.split("function rankLens(universe,lens", 1)[1].split("function brief(s)", 1)[0]
        self.assertIn("const canonical=(Array.isArray(universe)?universe:[]).filter(s=>eligible(s))", block)
        self.assertIn("const general=scoped.slice().sort", block)
        self.assertIn("rows:general.filter(s=>lensEligible(s,type))", block)
        self.assertNotIn("rankedCandidates(universe,type,sector)", block)
        self.assertNotIn("fallback.push(...general)", block)

    def test_general_shortlist_anchors_top_canonical_discovery_before_archetypes(self):
        source = read('market-opportunities.js')
        block = source.split("function rankLens(universe,lens", 1)[1].split("function brief(s)", 1)[0]
        self.assertIn("const anchorCount=Math.min(3,limit)", block)
        self.assertIn("for(const candidate of general.slice(0,anchorCount))", block)
        self.assertLess(
            block.index("for(const candidate of general.slice(0,anchorCount))"),
            block.index("while(selected.length<limit&&progressed)"),
        )
        self.assertIn("return diversify(pool,limit,{recoveryCap:Math.min(5,limit)})", block)

    def test_general_discovery_shortlist_has_diversification_guardrails(self):
        source = read('market-opportunities.js')
        self.assertIn('function diversify(rows,limit,{sectorCap=3,industryCap=2,recoveryCap=Infinity}={})', source)
        self.assertIn('return diversify(pool,limit,{recoveryCap:Math.min(5,limit)})', source)
        self.assertNotIn('for(const candidate of deferred)', source)
        self.assertIn('never refill with names that were', source)
        self.assertIn('diversify,rankLens', source)
        # Strategy-specific lenses remain pure rankings; only the general shortlist
        # applies presentation-level diversification.
        self.assertIn("if(lens!=='all')return rankedCandidates(universe,lens,sector).slice(0,limit)", source)

    def test_empty_lens_clears_previous_rows_instead_of_leaving_stale_candidates(self):
        source = read('market-opportunities.js')
        self.assertNotIn("if(!rows.length)return", source)
        self.assertIn("list.innerHTML=rows.map(s=>row(s,activeLens)).join('')", source)
        self.assertIn("||'empty'", source)

    def test_canonical_opportunities_own_podium_guide_and_static_styles(self):
        source = read('market-opportunities.js')
        css = read('market-opportunities.css')
        self.assertIn('function decorate(section)', source)
        self.assertIn('ux454-opportunity-guide', source)
        self.assertIn('ux454-podium-1', source)
        self.assertIn('ux454-rank', source)
        self.assertIn('data-market-ticker', source)
        self.assertEqual(source.count('new MutationObserver'), 1)
        self.assertIn("const root=document.getElementById('marketPrimary');if(!root)return", source)
        self.assertIn("function observerNeedsRefresh(root)", source)
        self.assertIn("return !!list && !list.dataset.ux453", source)
        self.assertIn("if(pending||!observerNeedsRefresh(root))return", source)
        self.assertIn("if(observerNeedsRefresh(root))opportunities()", source)
        self.assertIn("mo.observe(root,{childList:true,subtree:true})", source)
        self.assertNotIn("observe(document.body", source)
        self.assertIn("market-opportunities.css?v=1.2", source)
        self.assertIn("link.rel='stylesheet'", source)
        self.assertNotIn("document.createElement('style')", source)
        self.assertNotIn('s.textContent=', source)
        for selector in ('.ux453-opp{', '.ux454-opportunity-guide{', '.ux454-podium-1{', '.ux454-rank{'):
            self.assertIn(selector, css)

    def test_portfolio_badges_are_consolidated_into_classifier(self):
        source = read('portfolio-card-classifier.js')
        css = read('portfolio-card-classifier.css')
        for token in ('TROCAS INTELIGENTES','DUPLICAÇÃO DE EXPOSIÇÃO','CAPITAL NOVO'):
            self.assertIn(token, source)
        for token in ('.ux-card-badge.is-purple','.ux-card-badge.is-amber','.ux-card-badge.is-green'):
            self.assertIn(token, css)
        self.assertIn("version:'1.9'", source)

    def test_weekly_rotation_is_an_explainable_proxy_not_literal_fund_flow(self):
        market = read('market.js')
        ranker = read('scripts/opportunity_rank.py')
        shards = read('scripts/build_market_shards.py')
        css = read('market.css')
        self.assertIn('const WEEKLY_ROTATION_THEMES=[', market)
        self.assertIn('function weeklyRotationThemeRows()', market)
        self.assertIn('function renderWeeklyRotation()', market)
        self.assertIn('opportunity_return_5d_pct', market)
        self.assertIn('WEEKLY ROTATION · 5D', market)
        self.assertIn('O ranking continua baseado em preço + breadth', market)
        self.assertIn('Não representa subscrições/resgates de fundos', market)
        self.assertIn('"return_5d_pct": round(r5, 2)', ranker)
        self.assertIn('"opportunity_return_5d_pct": timing.get("return_5d_pct")', ranker)
        self.assertIn('"opportunity_return_5d_pct"', shards)
        self.assertIn('.market-rotation-row{', css)
        self.assertNotIn('weeklyFundFlowScore', market)


    def test_weekly_rotation_waiting_state_is_readable_and_not_fake_interactive(self):
        market = read('market.js')
        css = read('market.css')
        self.assertIn('market-rotation--waiting', market)
        self.assertIn('market-rotation-status', market)
        self.assertIn('A formar a primeira leitura semanal.', market)
        self.assertNotIn('Não tens de abrir este card.', market)
        self.assertIn('.market-rotation--waiting{background:var(--card2);color:var(--text)', css)
        self.assertIn('.market-rotation-wait span{', css)
        self.assertNotIn('data-rotation-toggle', market)

    def test_weekly_rotation_etf_flow_is_confirmation_not_ranking_alpha(self):
        market = read('market.js')
        shards = read('scripts/build_market_shards.py')
        css = read('market.css')
        self.assertIn('const WEEKLY_ROTATION_ETFS={', market)
        self.assertIn('function weeklyEtfConfirmation(label)', market)
        self.assertIn('fund_flow_1w_usd', market)
        self.assertIn('fund_return_1w_pct', market)
        self.assertIn('O ranking continua baseado em preço + breadth', market)
        rotation_block = market.split('function weeklyRotationThemeRows()', 1)[1].split('function renderWeeklyRotation()', 1)[0]
        self.assertIn('const rank=(med5||0)*1.4+(breadth-50)*.08+(med20||0)*.25', rotation_block)
        self.assertNotIn('flowUsd', rotation_block.split('const rank=', 1)[1].split(';', 1)[0])
        self.assertIn('FUND_AUM_HISTORY', shards)
        self.assertIn('def fund_flow_metrics(row: dict, history: dict, as_of: str)', shards)
        self.assertIn('expected_assets_without_flow = prior_assets * price_ratio', shards)
        self.assertIn('"fund_flow_1w_usd"', shards)
        self.assertIn('"fund_flow_1w_pct"', shards)
        self.assertIn('.market-rotation-name em{', css)

    def test_market_rebuild_marker_is_wired_to_canonical_pipeline(self):
        workflow = read('.github/workflows/update-market-data.yml')
        self.assertIn("'.github/triggers/market-data-rebuild.txt'", workflow)
        self.assertIn('python build_market_shards.py', workflow)
        self.assertIn('git add data/', workflow)

    def test_shared_worker_survives_hydration_and_blank_settings(self):
        app = read('app.js')
        html = read('index.html')
        self.assertIn('workerUrl: String((p.settings && p.settings.workerUrl) || DEFAULT_WORKER_URL).trim() || DEFAULT_WORKER_URL', app)
        self.assertIn('workerInput.value = (state.settings && state.settings.workerUrl) || DEFAULT_WORKER_URL', app)
        self.assertIn('state.settings.workerUrl = val || DEFAULT_WORKER_URL', app)
        self.assertIn('Worker global restaurado', app)
        self.assertIn('app.js?v=20260930v3', html)

    def test_shared_worker_default_and_rotation_contrast_are_explicit(self):
        app = read('app.js')
        market = read('market.js')
        css = read('market.css')
        self.assertIn('const DEFAULT_WORKER_URL = "https://delicate-bar-cc80.pedrossnunes.workers.dev"', app)
        self.assertIn('window.VestraRuntimeConfig = Object.freeze({ workerUrl: DEFAULT_WORKER_URL })', app)
        self.assertIn('workerUrl: DEFAULT_WORKER_URL', app)
        self.assertIn('window.VestraRuntimeConfig?.workerUrl', market)
        self.assertNotIn('market-rotation-wait-title', market)
        self.assertIn('market-rotation-wait-copy', market)
        self.assertIn('.market-rotation-wait-copy{color:#4f6472!important;opacity:1!important}', css)
        self.assertIn('.market-rotation-method__body,.market-rotation-method__body p{color:#4f6472!important}', css)

    def test_weekly_rotation_exposes_partial_evidence_coverage(self):
        market = read('market.js')
        self.assertIn('function weeklyRotationCoverage()', market)
        self.assertIn('weekly.length>=4', market)
        self.assertIn("${coverage.ready}/${coverage.total} temas · 5d", market)
        self.assertIn('Ainda a formar série:', market)
        self.assertIn('Um tema só entra no ranking com ≥4 ações com retorno semanal.', market)

    def test_weekly_rotation_separates_inflows_from_outflows(self):
        market = read('market.js')
        css = read('market.css')
        self.assertIn("function rotationEtfConfirms(etf,direction)", market)
        self.assertIn("const inflows=rows.filter(r=>r.med5>0 && r.breadth>=50 && rotationEtfConfirms(r.etf,1))", market)
        self.assertIn("const medianRank=rotationMedian(rows.map(r=>r.rank))", market)
        self.assertIn("!inflowLabels.has(r.label)", market)
        self.assertIn("rotationEtfConfirms(r.etf,-1)", market)
        self.assertIn("!relativeLabels.has(r.label)", market)
        self.assertIn("renderRotationGroup('Entradas confirmadas'", market)
        self.assertIn("renderRotationGroup('A ganhar força relativa'", market)
        self.assertIn("renderRotationGroup('Saídas confirmadas'", market)
        self.assertIn('Sem entradas absolutas confirmadas esta semana', market)
        self.assertIn('Preço forte · ETF não confirma', market)
        self.assertIn('Sem saídas confirmadas esta semana', market)
        self.assertNotIn('market-rotation-summary', market)
        self.assertIn('market-rotation-method', market)
        self.assertIn('Como é calculado?', market)
        self.assertIn('market-rotation-group__head--compact', market)
        self.assertIn(".slice(0,3)", market)
        self.assertIn('.market-rotation-method{', css)
        self.assertIn('.market-rotation-group__head--compact{', css)
        rendered = market.split('function renderWeeklyRotation()', 1)[1].split('function renderDiscover()', 1)[0]
        self.assertNotIn('class="market-rotation-intro"', rendered)
        self.assertNotIn('class="market-case-note market-rotation-note"', rendered)

    def test_service_worker_caches_canonical_modules(self):
        sw = read('sw.js')
        self.assertIn('const CACHE_NAME = "vestra-cache-', sw)
        self.assertIn('staleWhileRevalidate', sw)
        for module in (
            './market-live-overlay.js','./market-opportunities.js','./market-opportunities.css','./vestra-portfolio-hierarchy.js','./vestra-swap-lab.js',
            './market-company-brief.js','./market-metric-cleanup.js','./portfolio-collapsibles.js','./portfolio-card-classifier.js','./portfolio-diagnostics.js',
            './vestra-ai-brief.js','./portfolio-dossier-routing.js','./market-opportunity-lenses.js','./mobile-ui-refresh.js',
        ):
            self.assertIn(module, sw)
        self.assertNotIn('./vestra-portfolio-focus.js', sw)
        self.assertNotIn('./vestra-portfolio-focus.css', sw)

    def test_value_lens_requires_internal_valuation_support(self):
        source = read('market-opportunities.js')
        block = source.split("if(lens==='value'){", 1)[1].split("}", 1)[0]
        self.assertIn("fv!=null&&fv>=10", block)
        self.assertIn("['moderate','strong'].includes(support)", block)
        self.assertNotIn("pt!=null&&pt>=12", block)
        self.assertIn("val!=='overvalued'", block)

    def test_analyst_target_is_confirmation_not_fallback_alpha(self):
        source = read('market-opportunities.js')
        fallback = source.split('function fallbackUpsideSupport(s)', 1)[1].split('function discoveryScore(s)', 1)[0]
        discovery = source.split('function discoveryScore(s)', 1)[1].split('function low52Above(s)', 1)[0]
        self.assertIn('const analystPositive=pt!=null&&pt>=12', fallback)
        self.assertIn("valuationRobust&&revisionsPositiveCurrent&&!revisionsNegativeCurrent&&!durabilityNegative", fallback)
        self.assertIn("const analystPositive=pt!=null&&pt>=12", fallback)
        self.assertNotIn("(revisionsPositive||analystPositive)", fallback)
        self.assertNotIn('pt/7', discovery)


    def test_opportunity_copy_never_uses_analyst_target_as_fair_value_fallback(self):
        source = read('market-opportunities.js')
        self.assertNotIn("else if(pt!=null&&pt>10)b.push", source)
        self.assertNotIn("pt!=null?`target +", source)



if __name__ == '__main__':
    unittest.main(verbosity=2)
