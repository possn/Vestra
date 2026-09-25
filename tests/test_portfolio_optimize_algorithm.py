from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")

class PortfolioOptimizeAlgorithmTests(unittest.TestCase):
    def test_same_sector_alternatives_are_conviction_first(self):
        s = read("market.js")
        self.assertIn("conv>=curConv+5 && score>=curScore+3", s)
        self.assertIn("if(isFund(r.stock)||!txt(r.stock.sector)", s)
        self.assertIn("[\'watch\',\'high\',\'severe\'].includes(txt(x.risk_gate))", s)
        self.assertIn("industryBonus", s)
        self.assertIn("conf==null||conf<60", s)
        self.assertIn("x.indirect<=currentIndirect+1.5", s)
        self.assertIn("convDelta*1.35+scoreDelta*.25+valuationBonus+industryBonus-overlapPenalty", s)
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
        self.assertGreaterEqual(s.count("evaluatePortfolioMove({"), 4)

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
