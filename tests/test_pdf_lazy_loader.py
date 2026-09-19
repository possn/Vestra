from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")
APP = (ROOT / "app.js").read_text(encoding="utf-8")


class LazyPdfLoaderTests(unittest.TestCase):
    def test_pdfjs_is_not_injected_during_startup(self):
        self.assertNotIn("pdfjs-dist@3.11.174/build/pdf.min.js", INDEX)
        self.assertNotIn("window.pdfjsLib = null", INDEX)

    def test_pdf_loader_is_single_flight_bounded_and_retryable(self):
        start = APP.index("let __pfPdfJsPromise = null;")
        end = APP.index("async function extractTextFromPDF", start)
        block = APP[start:end]
        self.assertIn("if (__pfPdfJsPromise) return __pfPdfJsPromise;", block)
        self.assertIn('script[data-pf-pdfjs="1"]', block)
        self.assertIn("__pfPdfJsPromise = null;", block)
        self.assertIn("Timeout a carregar pdf.js", block)
        self.assertIn("Math.max(1, Number(timeoutMs) || 7000)", block)
        self.assertIn("s.remove();", block)

    def test_pdf_parser_requests_loader_on_demand(self):
        start = APP.index("async function extractTextFromPDF")
        end = APP.index("\nasync function", start + 20)
        block = APP[start:end]
        self.assertIn("await ensurePdfJsLoaded(7000)", block)
        self.assertIn("lib.getDocument", block)

    def test_worker_url_is_configured_after_lazy_load(self):
        self.assertIn(
            "https://cdn.jsdelivr.net/npm/pdfjs-dist@3.11.174/build/pdf.worker.min.js",
            APP,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
