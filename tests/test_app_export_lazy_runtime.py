from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")
APP = (ROOT / "app.js").read_text(encoding="utf-8")
RUNTIME = (ROOT / "app-export-runtime.js").read_text(encoding="utf-8")
SW = (ROOT / "sw.js").read_text(encoding="utf-8")


class LazyAppExportRuntimeTests(unittest.TestCase):
    def test_export_runtime_is_not_in_initial_html(self):
        self.assertNotIn('src="app-export-runtime.js', INDEX)
        self.assertIn('app.js?v=20260921v12', INDEX)

    def test_app_loads_exports_only_on_demand_with_retry(self):
        self.assertIn("function ensureAppExportRuntime()", APP)
        self.assertIn("script.src = 'app-export-runtime.js?v=1.0';", APP)
        self.assertIn("appExportRuntimePromise = null;", APP)
        self.assertIn("12000", APP)

    def test_all_export_entry_points_use_lazy_runtime(self):
        self.assertIn("runtime.exportBackup", APP)
        self.assertIn("runtime.exportCashflowCsv", APP)
        self.assertIn("runtime.exportPortfolioCsv", APP)
        self.assertIn("runtime.exportPortfolioXlsx", APP)
        self.assertIn("runtime.exportFiscalCsv", APP)
        self.assertIn("runtime.exportAnnualReport", APP)
        self.assertNotIn("function downloadText(", APP)

    def test_runtime_preserves_offline_and_network_first_delivery(self):
        self.assertIn('"./app-export-runtime.js"', SW)
        self.assertIn('"app-export-runtime.js"', SW)

    def test_runtime_owns_backup_safety_and_ios_download_contract(self):
        self.assertIn("value instanceof Set", RUNTIME)
        self.assertIn("value instanceof Map", RUNTIME)
        self.assertIn("seen.has(next)", RUNTIME)
        self.assertIn("document.body.appendChild(anchor)", RUNTIME)
        self.assertLess(RUNTIME.index("document.body.appendChild(anchor)"), RUNTIME.index("anchor.click()"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
