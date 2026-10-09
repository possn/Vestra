from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class SharedEditorialSpacing(unittest.TestCase):
 def test_same_spacing_shared_across_views(self):
  base=(ROOT/"vestra-design-v2.css").read_text()
  portfolio=(ROOT/"vestra-portfolio-v2.css").read_text()
  market=(ROOT/"vestra-market-surfaces-v2.css").read_text()
  for item in ["--vestra-space-card:16px","--vestra-space-section:17px","--vestra-space-controls:12px"]:
   self.assertIn(item,base)
  self.assertIn("gap:var(--vestra-space-card)",portfolio)
  self.assertIn("gap:var(--vestra-space-controls)",portfolio)
  self.assertIn("gap:var(--vestra-space-section)",market)
 def test_cache(self):
  html=(ROOT/"index.html").read_text()
  for item in ["vestra-design-v2.css?v=6","vestra-portfolio-v2.css?v=8","vestra-market-surfaces-v2.css?v=6"]:
   self.assertIn(item,html)
