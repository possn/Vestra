"""Separate observed scanner watch options from the canonical risk-gated pick."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class PrebreakoutWatchOptionsContract(unittest.TestCase):
    def test_watch_options_retain_risk_distinction_and_navigation(self):
        script=(ROOT/"vestra-intelligence-home.js").read_text()
        self.assertIn("const watchOptions = rows.filter(row => row.vcpConfirmed === true",script)
        self.assertIn("row.breakoutExtensionPct <= 0",script)
        self.assertIn("slice(0,4)",script)
        self.assertIn("const pick = hasCanonicalFocus ? canonicalPick : qualified[0]",script)
        self.assertIn("showWatchOptions();",script)
        self.assertIn("Resultados próximos · não elegível para destaque",script)
        self.assertIn("Resultados desconhecidos · não elegível para destaque",script)
        self.assertIn("button.dataset.vestraGo='market'",script)
        self.assertIn("button.dataset.vestraTicker=row.ticker",script)
        self.assertIn("Candidatos técnicos, não escolhas validadas",script)

    def test_stylesheet_loaded_without_removing_previous_scanner(self):
        html=(ROOT/"index.html").read_text()
        self.assertIn("vestra-prebreakout-home.css",html)
        self.assertIn("vestra-prebreakout-watch-options.css?v=20261029",html)
        css=(ROOT/"vestra-prebreakout-watch-options.css").read_text()
        self.assertIn("@media(max-width:760px)",css)
        self.assertIn(".vi-pb-watch-option:focus-visible",css)

if __name__=="__main__":
    unittest.main()
