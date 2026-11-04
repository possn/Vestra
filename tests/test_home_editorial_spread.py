"""Protect Vestra 2.0 sibling-based editorial grid without dropping live modules."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class EditorialSpreadTests(unittest.TestCase):
    def test_spread_uses_real_sibling_structure_and_has_mobile_fallback(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        css = (ROOT / "vestra-home-editorial-spread.css").read_text(encoding="utf-8")
        self.assertIn(
            'vestra-home-editorial-spread.css?v=20261104-sibling-grid', html
        )
        self.assertLess(html.index('vestra-home-first-look-order.css'),
                        html.index('vestra-home-editorial-spread.css'))
        self.assertIn("@media (min-width:1100px)", css)
        self.assertIn("@media (max-width:1099px)", css)
        for section in ("vi-home-overview", "vi-context-chapter", "vi-priorities",
                        "vi-risk-reading", "vi-regime-disclosure", "vi-research-details"):
            self.assertIn(".vi-shell>." + section, css)
        self.assertIn("grid-column:1/-1!important", css)
        self.assertIn("grid-template-columns:repeat(3,minmax(0,1fr))!important", css)
        self.assertIn("display:flex!important", css)

    def test_all_original_live_and_accessibility_hooks_remain(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        start = html.index('<section id="vestraIntelligenceHome"')
        end = html.index('<div class="vi-back-to-intelligence"', start)
        home = html[start:end]
        for hook in (
            'data-vi-wealth', 'data-vi-income-monthly', 'data-vi-privacy',
            'data-vi-canonical-score', 'data-vi-pulse-cnn',
            'data-vi-pulse-aaii', 'data-vi-pulse-coverage',
            'data-vi-canonical-news-list', 'data-vi-canonical-event-list',
            'data-vestra-portfolio-evidence', 'data-vestra-decision-state',
            'data-vi-canonical-risk-title', 'data-vestra-horizon-ledger',
            'data-vestra-go="portfolio"', 'data-vestra-go="market"',
        ):
            with self.subTest(hook=hook):
                self.assertIn(hook, home)
        self.assertNotIn("display:none", (ROOT / "vestra-home-editorial-spread.css").read_text(encoding="utf-8"))
        self.assertNotIn("MutationObserver", (ROOT / "vestra-home-editorial-spread.css").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
