from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
HTML=(ROOT/'index.html').read_text(encoding='utf-8')
CSS=(ROOT/'vestra-intelligence-detail-dark-v2.css').read_text(encoding='utf-8')
class IntelligenceDarkRollback(unittest.TestCase):
    def test_unreadable_dark_layer_is_disabled(self):
        self.assertNotIn('<link href="vestra-intelligence-detail-dark-v2.css',HTML)
        self.assertIn('Temporarily disabled: expanded Dashboard dark-layer contrast regression',HTML)
    def test_problematic_sheet_is_kept_for_diagnosis_not_loaded(self):
        self.assertIn('background:#071d1b!important',CSS)
        self.assertIn('vestra-intelligence.css?v=',HTML)
if __name__=='__main__': unittest.main()
