from pathlib import Path
import unittest
from _css_contrast import assert_contrast
ROOT=Path(__file__).resolve().parents[1]
class ResearchDossierContrast(unittest.TestCase):
    def test_dark_card_captions_and_metrics(self):
        # The dossier cards are now light (#f5f3ed); the invariant is that
        # captions and metrics keep >=4.5:1 ink on that surface.
        css=(ROOT/"vestra-market-dossier-content-v2.css").read_text()
        self.assertIn("#marketSheet .market-dossier-smart-grid span",css)
        for sel in ("#marketSheet .market-dossier-smart-grid span",
                    "#marketSheet .market-dossier-smart-grid small",
                    "#marketSheet .market-dossier-smart-grid strong"):
            assert_contrast(self,css,sel,"#f5f3ed")
    def test_version(self):
        self.assertIn("vestra-market-dossier-content-v2.css?v=",(ROOT/"index.html").read_text())
