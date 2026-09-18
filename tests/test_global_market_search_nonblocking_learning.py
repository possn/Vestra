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

    def test_global_open_rechecks_request_ownership_before_canonical_navigation(self):
        marker = "const stock=market?.registerExternalStock?.(stockData);"
        start = GLOBAL.index(marker)
        tail = GLOBAL[start:]
        self.assertIn("if(request!==remoteOpenSeq) return false;", tail)
        self.assertIn("const nav=window.VestraNavigation;", tail)
        self.assertIn("await nav.openCompany(stock.ticker,{origin:'market'});", tail)
        self.assertLess(
            tail.index("if(request!==remoteOpenSeq) return false;"),
            tail.index("const nav=window.VestraNavigation;")
        )
        self.assertNotIn("content.innerHTML", tail)
        self.assertNotIn("remote-live", tail)

    def test_runtime_and_loader_versions_match(self):
        self.assertIn("version:'1.8'", GLOBAL)
        self.assertIn("market-global-search.js?v=1.8", BOOT)


if __name__ == "__main__":
    unittest.main(verbosity=2)
