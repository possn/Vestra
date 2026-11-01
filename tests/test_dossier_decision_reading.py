"""Decision-first dossier presentation contract: progressive, legible and responsive."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class DossierDecisionReadingTests(unittest.TestCase):
 def test_existing_stylesheet_remains_loaded(self):
  html=(ROOT/"index.html").read_text(encoding="utf-8")
  self.assertIn("vestra-dossier-decision-v2.css",html)
 def test_dossier_structure_and_readability(self):
  css=(ROOT/"vestra-dossier-decision-v2.css").read_text(encoding="utf-8")
  for expected in (".v2-dossier-decision-stage__head", ".v2-dossier-decision-stage__grid", "min-width:0", "overflow-wrap:anywhere", "@media(max-width:760px)", "grid-template-columns:minmax(0,1fr)"):
   self.assertIn(expected,css)
  for forbidden in ("display:none","visibility:hidden","pointer-events:none","position:fixed"):
   self.assertNotIn(forbidden,css)
if __name__=="__main__":unittest.main()
