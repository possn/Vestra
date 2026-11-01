"""Screen-reported Home market density and bottom navigation clearance contract."""
from pathlib import Path
import unittest
R=Path(__file__).resolve().parents[1]
class HomeSentimentDensityTests(unittest.TestCase):
 def test_live_sources_survive_compact_mobile_layout(self):
  html=(R/"index.html").read_text(encoding="utf-8")
  css=(R/"vestra-home-first-look-order.css").read_text(encoding="utf-8")
  rules=css.split("Screen-verified Home correction:",1)[1]
  for marker in ('data-vi-canonical-score','data-vi-canonical-label','data-vi-pulse-cnn','data-vi-pulse-aaii','data-vi-pulse-coverage','data-vi-canonical-news-list'):
   self.assertIn(marker,html)
  for rule in ('.vi-sentiment-orb','.vi-live-pulse>div','grid-template-columns:repeat(3,minmax(0,1fr))','padding-bottom:max(120px','env(safe-area-inset-bottom'):
   self.assertIn(rule,rules)
  for forbidden in ('display:none','visibility:hidden','pointer-events:none'):
   self.assertNotIn(forbidden,rules)
if __name__=="__main__":unittest.main()
