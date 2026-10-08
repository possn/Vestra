"""Contract: only canonically rendered states, no invented decision engine."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class HomeDecisionBridgeTests(unittest.TestCase):
 def test_canonical_state_bridge(self):
  js=(ROOT/'vestra-intelligence-home.js').read_text()
  html=(ROOT/'index.html').read_text()
  market=(ROOT/'market.js').read_text()
  self.assertIn("['Rever', 'Atenção', 'Acompanhar', 'Dados parciais', 'Estável']",js)
  self.assertIn("sheet.dataset.tool === 'portfolio'",js)
  self.assertIn("sheet.querySelector('.market-decision-center[data-vpu-state]')",js)
  self.assertIn("vestra:market-sheet-changed",js)
  self.assertIn("data-vestra-decision-state",html)
  self.assertIn('data-vpu-state="${esc(decisionState)}"',market)
  self.assertNotIn("fetch(",js[js.index('function syncDecisionCenter('):js.index('function init()')])
if __name__=='__main__': unittest.main()
