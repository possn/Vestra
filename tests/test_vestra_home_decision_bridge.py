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
  self.assertIn("sheet?.dataset.tool === 'portfolio'",js)
  self.assertIn("sheet.querySelector('.market-decision-center[data-vpu-state]')",js)
  self.assertIn("vestra:market-sheet-changed",js)
  self.assertIn("vestra:local-state-writing",js)
  self.assertIn("lastDecision = null",js)
  self.assertIn("vestra:local-state-writing",(ROOT/'app.js').read_text())
  self.assertIn("let lastDecision = null",js)
  self.assertIn("15 * 60 * 1000",js)
  self.assertIn("const currentReading = Boolean(center",js)
  self.assertIn("!currentReading ? 'stale'",js)
  self.assertIn("leitura anterior da sessão · confirmar após alterações à carteira",js)
  self.assertNotIn("localStorage",js)
  self.assertNotIn("sessionStorage",js)
  self.assertIn("data-vestra-decision-state",html)
  self.assertIn("data-vestra-model-evidence",html)
  self.assertIn("validação preditiva e fora da amostra não demonstrada",js)
  self.assertIn('data-vpu-state="${esc(decisionState)}"',market)
  self.assertNotIn("fetch(",js[js.index('function syncDecisionCenter('):js.index('function init()')])
if __name__=='__main__': unittest.main()
