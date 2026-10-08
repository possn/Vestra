"""Feature flag contract: preview must never hijack default dashboard."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class IntelligenceHomeTests(unittest.TestCase):
    def test_opt_in_only_and_no_financial_mutations(self):
        html=(ROOT/"index.html").read_text(encoding="utf-8")
        js=(ROOT/"vestra-intelligence-home.js").read_text(encoding="utf-8")
        css=(ROOT/"vestra-intelligence.css").read_text(encoding="utf-8")
        self.assertIn('id="vestraIntelligenceHome"',html)
        self.assertIn('data-vestra-intelligence="1"',html)
        self.assertIn('id="vestraIntelligenceHome"',html)
        self.assertIn('aria-label="Vestra Intelligence',html)
        self.assertIn(' hidden>',html)
        self.assertIn("params.get('vestra2') === '1'",js)
        self.assertIn("if (!enabled) return",js)
        self.assertIn("['market', 'portfolio', 'dashboard']",js)
        self.assertNotIn("innerHTML",js)
        self.assertNotIn("state.assets",js)
        self.assertIn("#vestraIntelligenceHome[hidden]",css)
if __name__=="__main__": unittest.main()
