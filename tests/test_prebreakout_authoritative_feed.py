from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
JS=(ROOT/'market-opportunities.js').read_text(encoding='utf-8')
LOADER=(ROOT/'market-static-universe.js').read_text(encoding='utf-8')
class AuthoritativePrebreakoutTests(unittest.TestCase):
    def test_backend_feed_replaces_legacy_scanner(self):
        self.assertIn('let prebreakoutFeedAuthoritative=false;',JS)
        self.assertIn('prebreakoutFeedAuthoritative=true;',JS)
        fn=JS.split('function breakoutSetup(stock)',1)[1].split('function confirmed(s)',1)[0]
        self.assertLess(fn.index('if(prebreakoutFeedAuthoritative)return null;'),fn.index('const bars='))
    def test_cache_reloads_updated_script(self):
        self.assertIn('market-opportunities.js?v=1.13',LOADER)
if __name__=='__main__':unittest.main()
