from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
HOME=(ROOT/"vestra-intelligence-home.js").read_text(encoding="utf-8")
INDEX=(ROOT/"index.html").read_text(encoding="utf-8")
class WealthImportRefreshTests(unittest.TestCase):
    def test_hero_refreshes_after_import_state_write(self):
        marker="window.addEventListener('vestra:local-state-writing', () => {"
        self.assertIn(marker, HOME)
        listener=HOME.split(marker,1)[1].split("\n    });",1)[0]
        self.assertIn("syncWealthHero(host)", listener)
        self.assertIn("250, 1200", listener)
    def test_mobile_visibility_and_cache_contract(self):
        self.assertIn("document.addEventListener('visibilitychange'", HOME)
        self.assertIn("window.addEventListener('pageshow'", HOME)
        self.assertIn("vestra-intelligence-home.js?v=14", INDEX)
if __name__=="__main__":unittest.main()
