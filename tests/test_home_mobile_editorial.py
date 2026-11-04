"""Regression contracts for the mobile-first, source-preserving Vestra Home."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "vestra-home-mobile-editorial.css"

class MobileEditorialTests(unittest.TestCase):
    def test_stylesheet_is_last_home_layer_and_versioned(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        link = 'vestra-home-mobile-editorial.css?v=20261104-mobile-reading'
        self.assertIn(link, html)
        self.assertLess(html.index('vestra-home-editorial-spread.css'),
                        html.index(link))
        self.assertLess(html.index(link), html.index('</head>'))

    def test_mobile_editorial_layout_preserves_live_modules(self):
        css = CSS.read_text(encoding="utf-8")
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("@media (max-width:760px)", css)
        self.assertIn("@media (max-width:360px)", css)
        for selector in (
            ".vi-shell>.vi-home-overview", ".vi-shell>.vi-context-chapter",
            ".vi-shell>.vi-priorities", ".vi-shell>.vi-risk-reading",
            ".vi-shell>.vi-regime-disclosure", ".vi-shell>.vi-research-details",
        ):
            self.assertIn(selector, css)
        for hook in (
            "data-vi-wealth", "data-vi-privacy", "data-vi-income-monthly",
            "data-vi-canonical-score", "data-vi-pulse-cnn",
            "data-vi-pulse-aaii", "data-vi-canonical-news-list",
            "data-vi-canonical-event-list", "data-vestra-portfolio-evidence",
            "data-vi-canonical-risk-title", "data-vestra-horizon-ledger",
        ):
            self.assertIn(hook, html)
        self.assertNotIn("display:none", css)
        self.assertNotIn("MutationObserver", css)

if __name__ == "__main__":
    unittest.main()
