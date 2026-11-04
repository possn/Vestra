"""Market editorial shell: research navigation remains functional and compact."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class MarketEntryEditorialTests(unittest.TestCase):
 def test_entry_css_last_and_versioned(self):
  html=(ROOT/'index.html').read_text(encoding='utf-8')
  link='vestra-market-entry-editorial.css?v=20261104-research'
  self.assertIn(link,html)
  self.assertLess(html.index('vestra-market-olive-continuity-v2.css'),html.index(link))
  self.assertLess(html.index(link),html.index('</head>'))
 def test_market_controls_live_and_mobile_mode_scroll_preserved(self):
  html=(ROOT/'index.html').read_text(encoding='utf-8')
  view=html.split('id="viewMarket"',1)[1].split('id="marketSheet"',1)[0]
  for ident in ('marketApp','marketSearch','marketSuggestions','marketPrimary'):
   with self.subTest(ident=ident):
    self.assertIn('id="'+ident+'"',view)
  for selector in ('data-market-mode="discover"','data-market-mode="funds"',
                   'data-market-mode="crypto"','data-market-mode="smart"',
                   'data-market-mode="watch"','data-market-mode="lows"',
                   'data-market-tool="scanner"','data-market-tool="portfolio"'):
   self.assertIn(selector,view)
  css=(ROOT/'vestra-market-entry-editorial.css').read_text(encoding='utf-8')
  self.assertIn('overflow-x:auto!important',css)
  self.assertIn('@media(max-width:600px)',css)
  self.assertNotIn('MutationObserver',css)
  self.assertNotIn('display:none',css)

if __name__=='__main__':
 unittest.main()
