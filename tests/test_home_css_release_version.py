"""Home stylesheet release version follows the compact sentiment fix."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class HomeStylesheetVersionTests(unittest.TestCase):
 def test_home_uses_current_versioned_stylesheet(self):
  html=(ROOT/"index.html").read_text(encoding="utf-8")
  css=(ROOT/"vestra-home-first-look-order.css").read_text(encoding="utf-8")
  self.assertIn("vestra-home-first-look-order.css?v=20261101-compact-sentiment",html)
  self.assertNotIn("vestra-home-first-look-order.css?v=20261101-neutral-risk",html)
  self.assertIn("Screen-verified Home correction: compact market sentiment",css)
if __name__=="__main__": unittest.main()
