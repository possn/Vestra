"""Portfolio holdings editorial reading reuses dynamic list and canonical data."""
from pathlib import Path
import unittest
R=Path(__file__).resolve().parents[1]
class PortfolioHoldingsReadingTests(unittest.TestCase):
 def test_existing_hosts_preserved(self):
  html=(R/"index.html").read_text(encoding="utf-8")
  css=(R/"vestra-portfolio-v2.css").read_text(encoding="utf-8")
  section=css.split("Portfolio holdings: editorial reading order",1)[1]
  for value in ('id="itemsList"','id="itemsSub"','id="qSearch"','id="qSort"','id="btnPortfolioFilters"'):
   self.assertIn(value,html)
  for value in ('#itemsList>.item','.item__l','.item__t','.item__s','.item__v','font-variant-numeric:tabular-nums','@media(max-width:600px)'):
   self.assertIn(value,section)
  for bad in ('display:none','visibility:hidden','pointer-events:none'):
   self.assertNotIn(bad,section)
if __name__=="__main__":unittest.main()
