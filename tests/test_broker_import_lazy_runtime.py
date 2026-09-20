from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")
APP = (ROOT / "app.js").read_text(encoding="utf-8")
LOADER = (ROOT / "app-broker-import-loader.js").read_text(encoding="utf-8")


class LazyBrokerImportRuntimeTests(unittest.TestCase):
    def test_broker_workbook_and_parsers_are_not_in_initial_html(self):
        self.assertNotIn('src="app-broker-identity-data.js', INDEX)
        self.assertNotIn('src="app-broker-workbook.js', INDEX)
        self.assertNotIn('src="app-broker-parsers.js', INDEX)
        self.assertIn('src="app-broker-import-loader.js?v=1.1"', INDEX)

    def test_loader_preserves_dependency_order_and_retryability(self):
        self.assertIn("function ensureIdentityData()", LOADER)
        self.assertIn("function ensureWorkbook()", LOADER)
        self.assertIn("function ensureParsers()", LOADER)
        self.assertIn("app-broker-workbook.js?v=1.0", LOADER)
        self.assertIn("app-broker-parsers.js?v=1.0", LOADER)
        self.assertIn("app-broker-identity-data.js?v=1.0", LOADER)
        self.assertLess(
            LOADER.index("ensureWorkbook()"),
            LOADER.index("app-broker-parsers.js?v=1.0"),
        )
        self.assertIn("workbookPromise = null;", LOADER)
        self.assertIn("parsersPromise = null;", LOADER)
        self.assertIn("identityDataPromise = null;", LOADER)
        self.assertIn("const TIMEOUT_MS = 12000;", LOADER)

    def test_app_bootstrap_no_longer_requires_broker_parser_globals(self):
        prefix = APP[:APP.index("/* ─── MARKET CLIENT")]
        self.assertNotIn("window.VestraBrokerWorkbook || {}", prefix)
        self.assertNotIn("window.VestraBrokerParsers || {}", prefix)
        self.assertIn("async function ensureBrokerWorkbookRuntime()", prefix)
        self.assertIn("async function ensureBrokerParsersRuntime()", prefix)
        self.assertIn("async function ensureBrokerIdentityRuntime()", prefix)

    def test_import_paths_load_runtime_on_demand(self):
        broker_start = APP.index("async function importBrokerFiles(files)")
        broker_end = APP.index("\nasync function", broker_start + 10)
        broker = APP[broker_start:broker_end]
        self.assertIn("ensureBrokerParsersRuntime()", broker)
        self.assertIn("ensureBrokerIdentityRuntime()", broker)
        self.assertIn("parseBrokerImportFile(file)", broker)

        bank_start = APP.index("async function importBankFile(file)")
        bank_end = APP.index("\nasync function", bank_start + 10)
        bank = APP[bank_start:bank_end]
        self.assertIn("await ensureBrokerWorkbookRuntime()", bank)
        self.assertIn("fileToText(file)", bank)

    def test_app_rollout_is_versioned(self):
        self.assertIn("app.js?v=20260920v2", INDEX)

    def test_identity_repairs_are_deferred_but_precede_quote_refresh(self):
        self.assertIn("await ensureAndRepairBrokerIdentities({ persist: true });", APP)
        idle_start = APP.index("// Load the legacy identity authority after first paint")
        idle = APP[idle_start:idle_start + 700]
        self.assertLess(
            idle.index("ensureAndRepairBrokerIdentities({ persist: true })"),
            idle.index("autoRefreshQuotesIfStale()"),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
