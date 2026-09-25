from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")

class ScoreSemanticContractTests(unittest.TestCase):
    def test_analyst_evidence_stays_outside_core_score(self):
        analyst = read("scripts/analyst.py")
        score = read("scripts/score.py")
        self.assertIn("deliberately keeps analyst data OUT of the core Finscanner score", analyst)
        self.assertNotIn("analyst_", score)

    def test_confidence_preserves_raw_score_and_moderates_public_score(self):
        confidence = read("scripts/confidence.py")
        self.assertIn('raw_factor = _n(row.get("score"))', confidence)
        self.assertIn('"score_raw": raw_factor', confidence)
        self.assertIn('public_factor = None', confidence)
        self.assertIn('public_factor = min(public_factor, 59.0)', confidence)
        self.assertIn('public_factor = min(public_factor, 69.0)', confidence)

    def test_pipeline_orders_score_before_confidence_and_valuation(self):
        run = read("scripts/run.py")
        score_pos = run.index("scored = score_universe(raw)")
        confidence_pos = run.index("row.update(assess_confidence(row))")
        valuation_pos = run.index("row.update(assess_valuation(row))")
        thesis_pos = run.index("row.update(classify_thesis(row))")
        self.assertLess(score_pos, confidence_pos)
        self.assertLess(confidence_pos, valuation_pos)
        self.assertLess(valuation_pos, thesis_pos)

    def test_portfolio_conviction_is_a_downstream_synthesis_not_core_score(self):
        market = read("market.js")
        start = market.index("function portfolioConviction(s)")
        body = market[start:start + 1500]
        self.assertIn("parts.push([score,.55])", body)
        self.assertIn("parts.push([conf,.20])", body)
        self.assertIn("parts.push([est,.10])", body)
        self.assertIn("parts.push([val,.15])", body)
        self.assertIn("gate==='watch'", body)
        self.assertIn("gate==='high'", body)
        self.assertIn("gate==='severe'", body)

    def test_best_opportunities_is_distinct_discovery_layer(self):
        opp = read("scripts/opportunity_rank.py")
        self.assertIn("(score, .19)", opp)
        self.assertIn("(conf, .09)", opp)
        self.assertIn("(timing_score, .20)", opp)
        self.assertIn('_gate("confidence"', opp)
        self.assertIn("Risk Gate severe", opp)
        self.assertIn("opportunity_score", opp)

    def test_score_audit_keeps_weight_changes_diagnostic_only(self):
        doc = read("docs/score-validation.md")
        audit = read("docs/score-semantics-audit.md")
        self.assertIn("Do not optimize weights", doc)
        self.assertIn("Production weights changed: **no**", audit)
        self.assertIn("dependency overlap", audit)
        self.assertIn("Discovery Engine", audit)
        self.assertIn("Portfolio Decision Engine", audit)

if __name__ == "__main__":
    unittest.main(verbosity=2)
