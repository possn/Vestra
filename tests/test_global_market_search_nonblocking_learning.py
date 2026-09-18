from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
GLOBAL = (ROOT / "market-global-search.js").read_text(encoding="utf-8")
BOOT = (ROOT / "market-company-brief.js").read_text(encoding="utf-8")


class GlobalMarketSearchNonblockingLearningTests(unittest.TestCase):
    def test_central_learning_is_not_on_user_visible_render_path(self):
        self.assertIn("async function learn(row, source)", GLOBAL)
        self.assertIn("await learnedApi()?.upsert?.(row, source)", GLOBAL)
        self.assertIn("void learnCentral(row);", GLOBAL)
        self.assertNotIn("await learnCentral(row);", GLOBAL)

    def test_remote_result_rechecks_ownership_before_canonical_refresh(self):
        self.assertIn("const request=++remoteOpenSeq", GLOBAL)
        self.assertIn("if(request!==remoteOpenSeq) return false", GLOBAL)
        self.assertIn("if(ownsRemoteOpen(request,ticker) || ownsRemoteOpen(request,canonicalTicker))", GLOBAL)
        self.assertIn("market.openTicker(canonicalTicker)", GLOBAL)
        self.assertNotIn("content.innerHTML=", GLOBAL)

    def test_runtime_and_loader_versions_match(self):
        self.assertIn("version:'1.9'", GLOBAL)
        self.assertIn("market-global-search.js?v=1.9", BOOT)


if __name__ == "__main__":
    unittest.main(verbosity=2)
