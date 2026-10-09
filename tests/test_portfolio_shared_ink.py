from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class PortfolioSharedInk(unittest.TestCase):
 def test_palette_preserves_existing_values(self):
  base=(ROOT/"vestra-design-v2.css").read_text()
  portfolio=(ROOT/"vestra-portfolio-v2.css").read_text()
  values={"hero-ink":"#f4efe6","hero-muted":"#bed1c5","hero-gold":"#cdb47c","gold-bright":"#d8bf85","light-ink":"#18343a","value-caption":"#e0eee7","light-muted":"#4d6464"}
  for key,value in values.items():
   self.assertIn("--vestra-portfolio-"+key+":"+value,base)
   self.assertIn("var(--vestra-portfolio-"+key+")",portfolio)
 def test_stylesheet_versions(self):
  html=(ROOT/"index.html").read_text()
  self.assertIn("vestra-portfolio-v2.css?v=5",html)
  self.assertIn("vestra-design-v2.css?v=3",html)
