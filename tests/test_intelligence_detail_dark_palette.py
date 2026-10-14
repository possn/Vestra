from pathlib import Path
import unittest
R=Path(__file__).resolve().parents[1]
CSS=(R/'vestra-intelligence-detail-dark-v2.css').read_text()
HTML=(R/'index.html').read_text()
class ExpandedHomePalette(unittest.TestCase):
 def test_only_legacy_open_expanded_dashboard_is_styled(self):
  self.assertIn('vi-preview-active:has(#vestraIntelligenceHome[data-legacy-open="true"])',CSS)
  self.assertIn('background:#071d1b!important',CSS)
  self.assertIn('background:#12342f!important',CSS)
  self.assertIn('color:#f4f0e7!important',CSS)
 def test_layer_is_last(self):
  self.assertIn('vestra-intelligence-detail-dark-v2.css?v=1',HTML)
  self.assertGreater(HTML.index('vestra-intelligence-detail-dark-v2.css?v=1'),HTML.index('vestra-home-density-v2.css?v=7'))
if __name__=='__main__':unittest.main()
