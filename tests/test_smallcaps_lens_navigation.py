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
        self.assertNotIn("row.append(normal,smallcapChip)",code)
        lenses=(ROOT/'market-opportunity-lenses.js').read_text()
        self.assertIn('data-vestra-lens="smallcap_breakout"',lenses)
        self.assertIn('data-vestra-lens="breakout"',lenses)
        self.assertIn("section.querySelector('.vestra-technical-lenses')?.remove()",code)
if __name__=='__main__':unittest.main()
