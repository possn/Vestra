from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
HTML=(ROOT/"index.html").read_text(encoding="utf-8")

class SingleHomeIntroTest(unittest.TestCase):
    def test_no_second_legacy_editorial_home(self):
        self.assertNotIn('class="dashboard-welcome v2-home-intro"',HTML)
        self.assertEqual(HTML.count('id="vestraIntelligenceHome"'),1)
        self.assertEqual(HTML.count('id="kpiNet"'),1)
    def test_patrimonial_tools_and_rollback_still_mounted(self):
        for item in ['id="viewDashboard"','id="btnReturnIntelligence"','class="card hero v2-home-stage"','id="btnDashboardPrivacy"','id="backupReminderCard"']:
            self.assertIn(item,HTML)
