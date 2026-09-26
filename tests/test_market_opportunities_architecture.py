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
        self.assertIn("market-opportunities.js?v=1.2", loader)
        self.assertIn("market-opportunity-lenses.js?v=3.1", loader)
        self.assertLess(loader.index("market-opportunities.js?v=1.2"), loader.index("market-opportunity-lenses.js?v=3.1"))
        self.assertNotIn('src="vestra-portfolio-focus.js', hotfix)
        self.assertNotIn("vestra-portfolio-focus.js", loader)
        self.assertNotIn("vestra-ux-v452.js", hotfix)
        self.assertNotIn("vestra-ux-v453.js", hotfix)
        self.assertNotIn("vestra-ux-v454.js", hotfix)

    def test_canonical_opportunity_engine_keeps_v453_contract(self):
        source = read('market-opportunities.js')
        for token in (
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


    def test_inflation_shield_is_an_explainable_portfolio_regime_lens(self):
        market = read('market.js')
        css = read('market.css')
        self.assertIn('function inflationShieldProfile(stock)', market)
        self.assertIn('function renderInflationShield(rows)', market)
        self.assertIn('INFLATION SHIELD · REGIME LENS', market)
        self.assertIn('Não altera Vestra Score, Discovery nem Portfolio Fit', market)
        self.assertIn('Proxy, não backtest', market)
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
        self.assertIn("ranked.sort((a,b)=>lensScore(b,lens)-lensScore(a,lens)", source)
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

    def test_strategy_lenses_are_tilts_not_second_alpha_engines(self):
        source = read('market-opportunities.js')
        block = source.split('function lensScore(s,lens){', 1)[1].split('function rankedCandidates', 1)[0]
        self.assertIn('const discovery=discoveryScore(s)||0', block)
        self.assertIn('discovery*.82', block)
        self.assertIn('lensTilt(s,lens)', block)
        self.assertNotIn('confidence_score', block)
        self.assertNotIn('conf*.', block)

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
        self.assertIn("mo.observe(root,{childList:true,subtree:true})", source)
        self.assertNotIn("observe(document.body", source)
        self.assertIn("market-opportunities.css?v=1.0", source)
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
        self.assertIn("version:'1.6'", source)

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


if __name__ == '__main__':
    unittest.main(verbosity=2)
