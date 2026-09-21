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

    def test_exact_validation_precedes_canonical_dossier_handoff(self):
        self.assertIn("const request=++remoteOpenSeq", GLOBAL)
        self.assertIn("const exactRows=await validateExactTicker(ticker);", GLOBAL)
        self.assertIn("row?.identity_verified===true", GLOBAL)
        self.assertIn("if(request!==remoteOpenSeq) return false", GLOBAL)
        self.assertIn("if(!exactProviderIdentity(ticker,d))", GLOBAL)
        self.assertIn("if(ownsRemoteOpen(request,ticker)) market.openTicker(ticker)", GLOBAL)
        self.assertNotIn("content.innerHTML=", GLOBAL)
        self.assertLess(
            GLOBAL.index("const exactRows=await validateExactTicker(ticker);"),
            GLOBAL.index("await nav.openCompany(ticker,{origin:'market'")
        )

    def test_runtime_and_loader_versions_match(self):
        self.assertIn("version:'2.1'", GLOBAL)
        self.assertIn("market-global-search.js?v=2.1", BOOT)
        self.assertIn("market-learned-universe.js?v=3.0", BOOT)


if __name__ == "__main__":
    unittest.main(verbosity=2)
