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
    def test_same_sector_alternatives_use_canonical_move_evaluation(self):
        s = read("market.js")
        self.assertIn("mode==='alternative'", s)
        self.assertIn("convictionGain>=5&&convDelta>0&&overlapDelta<1.5&&riskPenalty<5", s)
        self.assertIn("const decision=evaluatePortfolioMove({mode:'alternative'", s)
        self.assertIn("if(!decision.autoEligible||scoreDelta<3) return null", s)
        self.assertIn("industryBonus", s)
        self.assertIn("decision.convictionGain*1.35+scoreDelta*.25", s)
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
        self.assertIn("decision.evidence.penalty", s)
        self.assertIn("tier:decision.evidence.tier", s)
        self.assertIn("Number(b.autoEligible)-Number(a.autoEligible)", s)

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
        self.assertIn("const {riskPenalty,autoEligible,warnings}=decision", s)
        self.assertIn("if(!c.autoEligible||used.has", s)
        self.assertIn("const allocations=[], used=new Set(), sectorAdds=new Map()", s)
        self.assertIn("afterTotal*maxSector/100-c.sectorValue-(sectorAdds.get(c.sector)||0)", s)
        self.assertIn("manual:candidates.filter(x=>!x.autoEligible).slice(0,3)", s)
        self.assertIn("O capital fica por alocar.", s)
        self.assertNotIn("budgetMode='soft budget'", s)

    def test_multi_move_plan_never_falls_back_to_worsening_candidate(self):
        s = read("market.js")
        self.assertIn("return !usedDest.has(key)&&r.autoEligible&&cumulativeSectorPct<=maxSector+1", s)
        self.assertNotIn("|| sim.results.find(r=>!usedDest.has", s)
        self.assertIn("const usedDest=new Set(), sectorAdds=new Map()", s)
        self.assertIn("const sourcePressure=r=>", s)
        self.assertIn("const planSources=rows.filter(r=>!isFund(r.stock)", s)
        self.assertIn("positionPct-maxPosition", s)
        self.assertIn("sectorPct-maxSector", s)
        self.assertIn("Plano indicativo e conservador", s)

if __name__ == "__main__":
    unittest.main(verbosity=2)
