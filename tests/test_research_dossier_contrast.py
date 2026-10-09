from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class ResearchDossierContrast(unittest.TestCase):
    def test_dark_card_captions_and_metrics(self):
        css=(ROOT/"vestra-market-dossier-content-v2.css").read_text()
        self.assertIn("#marketSheet .market-dossier-smart-grid span",css)
        self.assertIn("color:#c6d9cd!important;-webkit-text-fill-color:#c6d9cd!important",css)
        self.assertIn("color:#f4efe6!important;-webkit-text-fill-color:#f4efe6!important",css)
    def test_version(self):
        self.assertIn("vestra-market-dossier-content-v2.css?v=2",(ROOT/"index.html").read_text())
