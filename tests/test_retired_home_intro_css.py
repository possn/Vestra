from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class RetiredIntroCss(unittest.TestCase):
    def test_obsolete_intro_selectors_gone(self):
        css=(ROOT/"vestra-home-stage-v2.css").read_text()
        self.assertNotIn(".v2-home-intro",css)
        self.assertIn(".v2-home-stage.card.hero",css)
    def test_financial_dom_preserved(self):
        html=(ROOT/"index.html").read_text()
        for key in ['id="kpiNet"','id="btnDashboardPrivacy"','id="backupReminderCard"']:
            self.assertIn(key,html)
