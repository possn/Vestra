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

    def test_rebalancer_marks_only_robust_positive_improvements_auto_eligible(self):
        s = read("market.js")
        self.assertIn("const autoEligible=tier!=='research'&&convictionGain>=2&&convDelta>0&&overlapDelta<2", s)
        self.assertIn("positionPct<=maxPos+1&&sectorPct<=maxSector+1&&riskPenalty<5", s)
        self.assertIn("Number(b.autoEligible)-Number(a.autoEligible)", s)
        self.assertIn("melhoria de convicção insuficiente", s)
        self.assertIn("aumenta overlap", s)
        self.assertIn("origem apenas para análise manual", s)
        self.assertIn("txt(stock.risk_gate)!==\'watch\'", s)

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
