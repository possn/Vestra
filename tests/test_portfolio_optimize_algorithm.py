from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")

class PortfolioSignalSeparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / "market.js").read_text(encoding="utf-8")

    def test_conviction_does_not_embed_confidence_or_risk_gate(self):
        block = self.source.split("function portfolioConviction(s){", 1)[1].split("\n  function holdingSymbol", 1)[0]
        self.assertNotIn("confidence_score", block)
        self.assertNotIn("risk_gate", block)
        self.assertIn("estimate_momentum_score", block)
        self.assertIn("valuation_signal", block)
        self.assertIn("thesis_direction", block)

    def test_confidence_and_risk_remain_explicit_decision_gates(self):
        action = self.source.split("function portfolioAction(", 1)[1].split("\n  const PORTFOLIO_TARGETS_KEY", 1)[0]
        evidence = self.source.split("function portfolioMoveEvidence(", 1)[1].split("\n  function evaluatePortfolioMove", 1)[0]
        self.assertIn("confidence_score", action)
        self.assertIn("risk_gate", action)
        self.assertIn("confidence_score", evidence)
        self.assertIn("risk_gate", evidence)


class PortfolioOptimizeAlgorithmTests(unittest.TestCase):
    def test_decision_center_prioritizes_signals_without_composite_health_score(self):
        s = read("market.js")
        block = s.split("function renderPortfolioDecisionCenter(", 1)[1].split("\n  function portfolioIntelligence(", 1)[0]
        self.assertIn("const structuralAlert=", block)
        self.assertIn("const decisionState=", block)
        self.assertIn("data-vpu-state=", block)
        self.assertIn("<small>Risk Fit</small>", block)
        self.assertNotIn("let health=100", block)
        self.assertNotIn("data-vpu-health=", block)
        self.assertNotIn("${health}/100", block)

    def test_portfolio_ui_treats_risk_fit_as_higher_is_better(self):
        s = read("vestra-portfolio-ui.js")
        self.assertIn("riskFit<65", s)
        self.assertIn("riskFit<85", s)
        self.assertIn("Risk Fit sólido", s)
        self.assertIn("healthBar('Risk Fit',m.risk)", s)
        self.assertNotIn("healthBar('Risco',m.risk,true)", s)
        self.assertIn("maior é melhor", s)

    def test_same_sector_alternatives_use_canonical_move_evaluation(self):
        s = read("market.js")
        self.assertIn("mode==='alternative'", s)
        self.assertIn("convictionGain>=5&&convDelta>0&&overlapDelta<1.5&&riskPenalty<5", s)
        self.assertIn("const decision=evaluatePortfolioMove({mode:'alternative'", s)
        self.assertIn("if(!decision.autoEligible||scoreDelta<3) return null", s)
        self.assertIn("const sameIndustry=!!txt(x.industry)&&txt(x.industry)===txt(r.stock.industry)", s)
        self.assertIn("||a.decision.overlapDelta-b.decision.overlapDelta", s)
        self.assertIn("||b.scoreDelta-a.scoreDelta", s)
        self.assertIn("||Number(b.sameIndustry)-Number(a.sameIndustry)", s)
        self.assertIn("||b.valuationRank-a.valuationRank", s)
        self.assertNotIn("decision.convictionGain*1.35+scoreDelta*.25", s)
        self.assertNotIn("const rank=decision.convictionGain", s)
        self.assertIn("Convicção +${a.convDelta.toFixed(0)}", s)

    def test_canonical_move_evaluator_owns_shared_eligibility(self):
        s = read("market.js")
        self.assertIn("function portfolioMoveEvidence(stock)", s)
        self.assertIn("function evaluatePortfolioMove({mode='replace'", s)
        self.assertIn("autoEligible=sourceAutomatable&&evidence.strict&&convictionGain>=2&&convDelta>0&&overlapDelta<2", s)
        self.assertIn("positionPct<=maxPos+1&&sectorPct<=maxSector+1&&riskPenalty<5", s)
        self.assertIn("autoEligible=evidence.strict&&riskPenalty<5", s)
        self.assertIn("mode==='scenario'", s)
        self.assertIn("melhoria de convicção insuficiente", s)
        self.assertIn("aumenta overlap", s)
        self.assertIn("origem apenas para análise manual", s)
        self.assertGreaterEqual(s.count("evaluatePortfolioMove({"), 5)

    def test_rebalancer_consumes_canonical_move_evaluator(self):
        s = read("market.js")
        self.assertIn("const decision=evaluatePortfolioMove({mode:'replace'", s)
        self.assertIn("riskPenalty,diversifies,valuationRank,tiltBonus", s)
        self.assertIn("tier:decision.evidence.tier", s)
        self.assertIn("Number(b.autoEligible)-Number(a.autoEligible)", s)
        self.assertNotIn("decision.evidence.penalty", s.split("function rebalanceSimulation", 1)[1].split("\n  function renderRebalanceResults", 1)[0])

    def test_portfolio_candidate_ordering_has_no_composite_fit_score(self):
        s = read("market.js")
        self.assertNotIn("const fitScore=Math.max", s)
        self.assertNotIn("fitScore:dest.fitScore", s)
        self.assertNotIn("r.fitScore.toFixed", s)
        self.assertIn("||b.convictionGain-a.convictionGain", s)
        self.assertIn("||a.overlapDelta-b.overlapDelta", s)
        self.assertIn("||a.riskPenalty-b.riskPenalty", s)
        self.assertIn("||b.sectorHeadroom-a.sectorHeadroom", s)
        self.assertIn("Não existe um score composto de Portfolio Fit", s)

    def test_fresh_capital_ordering_uses_explicit_dimensions_not_composite_score(self):
        s = read("market.js")
        block = s.split("function freshCapitalPlan(amount){", 1)[1].split("\n  function renderFreshCapitalPlan", 1)[0]
        self.assertNotIn("let score=conv+", block)
        self.assertNotIn("b.score-a.score", block)
        self.assertNotIn("score,capacity", block)
        self.assertIn("||b.conv-a.conv", block)
        self.assertIn("||b.sectorHeadroom-a.sectorHeadroom", block)
        self.assertIn("||a.indirect-b.indirect", block)
        self.assertIn("||b.valuationRank-a.valuationRank", block)
        self.assertIn("||b.tiltBonus-a.tiltBonus", block)

    def test_same_value_scenario_uses_canonical_move_evaluator(self):
        s = read("market.js")
        self.assertIn("const decision=evaluatePortfolioMove({mode:'scenario'", s)
        self.assertIn("const {convDelta,overlapDelta,riskPenalty,autoEligible,warnings}=decision", s)
        self.assertIn("if(autoEligible&&(convDelta>=.5||overlapDelta<=-1)) impact='Melhora'", s)
        self.assertIn("if(convDelta<=0||overlapDelta>=2||riskPenalty>=5||!decision.evidence.strict) impact='Piora'", s)
        self.assertIn("cruza convicção, overlap e orçamento de risco", s)

    def test_fresh_capital_allocates_only_strict_candidates_with_cumulative_sector_budget(self):
        s = read("market.js")
        self.assertIn("!['watch','high','severe'].includes(txt(x.risk_gate))", s)
        self.assertIn("const decision=evaluatePortfolioMove({mode:'fresh'", s)
        self.assertIn("const {tier,strict}=decision.evidence", s)
        self.assertIn("const warnings=[...decision.evidence.warnings]", s)
        self.assertNotIn("if(!c.autoEligible||used.has", s)
        self.assertIn("const baselineRisk=portfolioRiskProfile(rows,afterTotal)", s)
        self.assertIn("const riskAddSafe=(stock,amount)=>", s)
        self.assertIn("current>limit ? next<=current+.01 : next<=limit+.01", s)
        self.assertIn("const allocationsByTicker=new Map(), sectorAdds=new Map()", s)
        self.assertIn("const baseEligible=strict&&(targets.overlap!=='reduce'||indirect<2)", s)
        self.assertIn("const eligible=candidates.filter(c=>c.baseEligible).slice(0,5)", s)
        self.assertNotIn("const eligible=candidates.filter(c=>c.autoEligible).slice(0,5)", s)
        self.assertIn("while(remaining>=50&&progressed)", s)
        self.assertIn("const tranche=Math.min(50,remaining,sectorRoom,positionRoom)", s)
        self.assertIn("applyRiskAdd(cand.stock,tranche)", s)
        self.assertNotIn("const shares=[.5,.3,.2]", s)
        self.assertIn("manual:candidates.filter(x=>!x.baseEligible).slice(0,3)", s)
        self.assertIn("O capital fica por alocar.", s)
        self.assertNotIn("budgetMode='soft budget'", s)

    def test_etf_optimize_compares_like_for_like_without_new_super_score(self):
        s = read("market.js")
        self.assertIn("function sameFundExposure(source,candidate)", s)
        self.assertIn("function fundHoldingsOverlapPct(a,b)", s)
        self.assertIn("function findEtfOptimizeAlternatives(ranked,heldTickers)", s)
        self.assertIn("function renderEtfOptimizeCard(rows)", s)
        self.assertIn("overlap>=30||(sameCategory&&specific)", s)
        self.assertNotIn("overlap>=30||sameCategory", s)
        self.assertIn("txt(candidate?.ticker).toUpperCase().replace(/\\.[A-Z]+$/,'')", s)
        self.assertNotIn("txt(candidate?.ticker).toUpperCase().replace(/.[A-Z]+$/,'')", s)
        self.assertIn("scoreDelta>=3", s)
        self.assertIn("terSaving!=null&&terSaving>=0.05", s)
        self.assertIn("dupDelta!=null&&dupDelta<=-5", s)
        self.assertIn("if(scoreDelta<-2)return null", s)
        self.assertIn("if(terSaving!=null&&terSaving<-0.03)return null", s)
        self.assertIn("if(dupDelta!=null&&dupDelta>10)return null", s)
        self.assertIn("ETF OPTIMIZE · MESMA EXPOSIÇÃO", s)
        self.assertIn("não uma recomendação automática de troca", s)
        self.assertIn("Não altera Vestra Score, Discovery Score nem Portfolio Action", s)
        self.assertNotIn("etfOptimizeScore", s)

    def test_etf_optimize_is_separate_from_equity_portfolio_action(self):
        s = read("market.js")
        action = s.split("function portfolioAction(", 1)[1].split("\n  const PORTFOLIO_TARGETS_KEY", 1)[0]
        self.assertNotIn("etf_score", action)
        self.assertNotIn("findEtfOptimizeAlternatives", action)
        intelligence = s.split("function portfolioIntelligence(rows,total)", 1)[1].split("function buildMultiMovePlan", 1)[0]
        self.assertIn("const etfOptimizeRows=findEtfOptimizeAlternatives(ranked,heldTickers)", intelligence)
        self.assertIn("${etfOptimizeHtml}", intelligence)

    def test_multi_move_plan_never_falls_back_to_worsening_candidate(self):
        s = read("market.js")
        self.assertIn("return !usedDest.has(key)&&r.autoEligible&&cumulativeSectorPct<=maxSector+1", s)
        self.assertNotIn("|| sim.results.find(r=>!usedDest.has", s)
        self.assertIn("const baselineRisk=portfolioRiskProfile(rows,totalValue)", s)
        self.assertIn("const riskMoveSafe=(sourceStock,destination,amount)=>", s)
        self.assertIn("current>limit ? next<=current+.01 : next<=limit+.01", s)
        self.assertIn("const usedDest=new Set(), sectorDeltas=new Map()", s)
        self.assertIn("const projectedOverlap=totalOverlapDelta+r.overlapDelta", s)
        self.assertIn("targets.overlap==='reduce'?projectedOverlap<=0:projectedOverlap<2", s)
        self.assertIn("sectorDeltas.set(srcSector,(sectorDeltas.get(srcSector)||0)-sim.amount)", s)
        self.assertIn("applyRiskMove(sim.source,dest.stock,sim.amount)", s)
        self.assertIn("const sourcePressure=r=>", s)
        self.assertIn("const planSources=rows.filter(r=>!isFund(r.stock)", s)
        self.assertIn("positionPct-maxPosition", s)
        self.assertIn("sectorPct-maxSector", s)
        self.assertIn("Plano indicativo e conservador", s)

if __name__ == "__main__":
    unittest.main(verbosity=2)
