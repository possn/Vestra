"""Dossier 2.0 visual reading contracts preserve the live financial hosts."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
class DossierEditorialReadingTests(unittest.TestCase):
 def test_final_dossier_css_layer_is_after_market_entry(self):
  html=(ROOT/'index.html').read_text(encoding='utf-8')
  link='vestra-dossier-editorial-reading.css?v=20261104-research'
  self.assertIn(link,html)
  self.assertLess(html.index('vestra-market-entry-editorial.css'),html.index(link))
  self.assertLess(html.index(link),html.index('</head>'))
 def test_financial_component_and_close_hooks_untouched(self):
  html=(ROOT/'index.html').read_text(encoding='utf-8')
  for ident in ('id="marketSheet"','id="marketSheetContent"','data-market-close'):
   self.assertIn(ident,html)
  for file in ('vestra-dossier-decision-v2.css','vestra-market-dossier-shell-v2.css','vestra-market-dossier-content-v2.css'):
   self.assertIn(file,html)
  css=(ROOT/'vestra-dossier-editorial-reading.css').read_text(encoding='utf-8')
  for token in ('.v2-dossier-decision-stage','.v2-dossier-decision-stage__grid',
                '.market-detail-head','.market-metrics','.market-detail-card',
                '.market-tabs','.market-detail-disclosure'):
   self.assertIn(token,css)
  self.assertIn('@media(max-width:760px)',css)
  self.assertIn('@media(max-width:600px)',css)
  for forbidden in ('display:none','visibility:hidden','pointer-events:none','MutationObserver'):
   self.assertNotIn(forbidden,css)

if __name__=='__main__':
 unittest.main()
