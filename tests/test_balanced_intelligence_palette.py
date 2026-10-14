from pathlib import Path
import unittest
R=Path(__file__).resolve().parents[1]
CSS=(R/"vestra-intelligence-balanced-v2.css").read_text()
HTML=(R/"index.html").read_text()
class BalancedIntelligencePaletteTests(unittest.TestCase):
 def test_theme_is_scoped_to_expanded_detail_only(self):
  self.assertIn('vi-preview-active:has(#vestraIntelligenceHome[data-legacy-open="true"])',CSS)
  self.assertNotIn('body:has(',CSS)
 def test_green_wealth_has_light_ink_and_gold_label(self):
  self.assertIn('background:linear-gradient(138deg,#17443b',CSS)
  self.assertIn('color:#f5f0e4!important',CSS)
  self.assertIn('color:#dfc292!important',CSS)
 def test_original_cream_reading_cards_are_not_overridden(self):
  self.assertNotIn('.vi-context-',CSS)
  self.assertNotIn('.vi-market-reading',CSS)
  self.assertNotIn('.vi-canonical-card',CSS)
 def test_asset_is_referenced_after_existing_palette_and_bad_dark_asset_unloaded(self):
  self.assertIn('vestra-intelligence-balanced-v2.css?v=1',HTML)
  self.assertNotIn('<link href="vestra-intelligence-detail-dark-v2.css',HTML)
  self.assertGreater(HTML.index('vestra-intelligence-balanced-v2.css?v=1'),HTML.index('vestra-market-olive-continuity-v2.css?v=1'))
if __name__=="__main__":unittest.main()
