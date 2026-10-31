from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class SmallcapLensNavigation(unittest.TestCase):
    def test_canonical_card_is_found_without_mutable_title(self):
        code=(ROOT/'market-opportunities.js').read_text()
        self.assertIn("document.querySelector('#marketPrimary .market-section:has(.ux454-opportunity-guide)')",code)
        self.assertIn("root.querySelector('.market-section:has(.ux454-opportunity-guide)')",code)
        self.assertIn("Compressão|Small Caps|Value",code)
    def test_same_card_keeps_both_lenses(self):
        code=(ROOT/'market-opportunities.js').read_text()
        self.assertIn("row.append(normal,smallcapChip)",code)
        self.assertIn("selectLens('smallcap_breakout')",code)
        self.assertIn("selectLens('breakout')",code)
if __name__=='__main__':unittest.main()
