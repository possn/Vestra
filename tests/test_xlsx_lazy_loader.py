from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class LazyXlsxLoaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = (ROOT / "index.html").read_text(encoding="utf-8")
        cls.loader = (ROOT / "app-xlsx-loader.js").read_text(encoding="utf-8")
        cls.app = (ROOT / "app.js").read_text(encoding="utf-8")
        cls.workbook = (ROOT / "app-broker-workbook.js").read_text(encoding="utf-8")
        cls.parsers = (ROOT / "app-broker-parsers.js").read_text(encoding="utf-8")

    def test_sheetjs_is_not_in_the_critical_html_path(self):
        self.assertNotIn(
            '<script src="https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js"></script>',
            self.index,
        )
        self.assertIn('src="app-xlsx-loader.js?v=1.0"', self.index)

    def test_loader_is_single_flight_bounded_and_retryable(self):
        self.assertIn("if (window.XLSX) return Promise.resolve(window.XLSX);", self.loader)
        self.assertIn("if (loadPromise) return loadPromise;", self.loader)
        self.assertIn("const TIMEOUT_MS = 12000;", self.loader)
        self.assertIn("loadPromise = null;", self.loader)
        self.assertIn("script.remove();", self.loader)
        self.assertIn("script.dataset.vestraXlsx = '1';", self.loader)
        self.assertIn("version: '1.0'", self.loader)

    def test_excel_paths_request_loader_only_when_needed(self):
        self.assertIn("VestraXlsxLoader", self.workbook)
        self.assertIn("await ensureXlsx();", self.workbook)
        self.assertIn("VestraXlsxLoader", self.parsers)
        self.assertIn("await loader.ensure();", self.parsers)
        self.assertGreaterEqual(self.app.count("VestraXlsxLoader"), 3)
        self.assertIn("async function exportPortfolioXLSX()", self.app)
        self.assertIn("await loader.ensure();", self.app)

    def test_csv_and_pdf_paths_do_not_require_sheetjs(self):
        start = self.parsers.index("async function parseBrokerImportFile(file)")
        block = self.parsers[start:self.parsers.index("\nfunction parseTrading212HoldingsPdf", start)]
        pdf_branch = block[:block.index('if (name.endsWith(".xlsx")')]
        self.assertNotIn("VestraXlsxLoader", pdf_branch)


if __name__ == "__main__":
    unittest.main(verbosity=2)
