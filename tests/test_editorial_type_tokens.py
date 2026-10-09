from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class EditorialTypeTokens(unittest.TestCase):
 def test_shared_type_stacks(self):
  base=(ROOT/"vestra-design-v2.css").read_text()
  portfolio=(ROOT/"vestra-portfolio-v2.css").read_text()
  self.assertIn('--vestra-editorial-serif: Georgia, "Times New Roman", serif',base)
  self.assertIn("font-family:var(--vestra-editorial-serif)",portfolio)
  self.assertIn("font-family:var(--v2-font)",portfolio)
 def test_cache(self):
  html=(ROOT/"index.html").read_text()
  self.assertIn("vestra-design-v2.css?v=5",html)
  self.assertIn("vestra-portfolio-v2.css?v=7",html)
