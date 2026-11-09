"""Market research must not expose duplicate technical lenses or misleading scanner scores."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

def source(name):
    return (ROOT / name).read_text(encoding="utf-8")

class MarketResearchClarityTests(unittest.TestCase):
    def test_breakout_lab_is_not_mislabeled_general_scanner(self):
        html = source("index.html")
        self.assertIn('data-market-tool="scanner" aria-label="Abrir scanner de estratégias de investimento"', html)
        self.assertIn("<strong>Estratégias</strong>", html)
        self.assertNotIn("<strong>Breakout Lab</strong>", html)
        self.assertIn('data-market-mode="smart"', html)

    def test_single_canonical_prebreakout_and_smallcap_controls(self):
        lenses = source("market-opportunity-lenses.js")
        ranked = source("market-opportunities.js")
        self.assertEqual(lenses.count('data-vestra-lens="breakout"'), 1)
        self.assertEqual(lenses.count('data-vestra-lens="smallcap_breakout"'), 1)
        self.assertNotIn("createElement('button');smallcapChip", ranked)
        self.assertNotIn("row.append(normal,smallcapChip)", ranked)
        self.assertIn("section.querySelector('.vestra-technical-lenses')?.remove()", ranked)
        self.assertIn("window.VestraMarketOpportunities?.selectLens?.(activeLens,moreSectorValue())", lenses)

    def test_scanner_does_not_display_unrelated_vestra_score_as_strategy_score(self):
        runtime = source("market-analysis-tools-runtime.js")
        self.assertIn("return stockRow(stock, meta, num(r?.score))", runtime)
        self.assertIn("scannerScore == null ? num(stock?.score) : num(scannerScore)", runtime)
        self.assertIn("Score Scanner", runtime)

    def test_company_activity_is_explicit_and_never_invented(self):
        ranked = source("market-opportunities.js")
        runtime = source("market-analysis-tools-runtime.js")
        self.assertIn("long_business_summary", ranked)
        self.assertIn("business_description", runtime)
        self.assertIn("Atividade por descrever", ranked)
        self.assertIn("Atividade ainda não descrita nos dados disponíveis.", runtime)

if __name__ == "__main__":
    unittest.main()
