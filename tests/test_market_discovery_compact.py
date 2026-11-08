"""Discovery cards: condensed first look, unchanged evidence and ranking."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
JS=(ROOT/'market-opportunities.js').read_text(encoding='utf-8')
CSS=(ROOT/'market-opportunities.css').read_text(encoding='utf-8')
class DiscoveryCompactContracts(unittest.TestCase):
 def test_mobile_card_has_native_disclosure_with_all_evidence(self):
  self.assertIn('class="ux453-evidence-toggle" type="button" aria-expanded="false"',JS)
  self.assertIn('class="ux453-evidence-content" hidden',JS)
  self.assertIn('${whyNowHtml(s)}',JS)
  self.assertIn('${sleevePills}',JS)
  self.assertIn('Score Vestra ${Math.round(n(s?.score)||0)}',JS)
  self.assertIn('Timing ${Math.round(tm)}',JS)
  self.assertIn('event.stopPropagation()',JS)
  self.assertIn("market-opportunities.css?v=20261108-compact-evidence",JS)
 def test_compact_mobile_css_retains_touch_target_and_full_detail(self):
  self.assertIn('@media(max-width:600px)',CSS)
  self.assertIn('.ux453-evidence-content[hidden]',CSS)
  self.assertIn('min-height:44px',CSS)
  self.assertIn('.ux453-evidence-content[hidden]{display:none!important}',CSS)
if __name__=='__main__':unittest.main()
