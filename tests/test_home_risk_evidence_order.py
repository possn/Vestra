"""Home 2.0: risk detail follows decisions without duplicating a card surface."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class HomeRiskEditorialDetailTests(unittest.TestCase):
    def test_existing_canonical_reading_order_is_preserved(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        home = html.split('<section id="vestraIntelligenceHome"', 1)[1].split(
            '<div class="vi-back-to-intelligence">', 1)[0]
        sections = ("vi-market-reading", "vi-news-reading", "vi-events-reading")
        for section in sections:
            self.assertEqual(home.count(f'vi-canonical-card {section}"'), 1)
        self.assertEqual(home.count('vi-canonical-card vi-risk-reading"'), 1)
        self.assertLess(home.index("vi-market-reading"), home.index("vi-news-reading"))
        self.assertLess(home.index("vi-news-reading"), home.index("vi-events-reading"))
        self.assertLess(home.index("vi-events-reading"), home.index('class="vi-priorities"'))
        self.assertLess(home.index('class="vi-priorities"'), home.index("vi-risk-reading"))
        self.assertLess(home.index("vi-risk-reading"), home.index('class="vi-regime-disclosure"'))

    def test_live_risk_metrics_and_navigation_are_untouched(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        home = html.split('<section id="vestraIntelligenceHome"', 1)[1].split(
            '<div class="vi-back-to-intelligence">', 1)[0]
        for marker in ("data-vi-canonical-risk-title", "data-vi-canonical-risk",
                       "data-vi-canonical-risk-value",
                       'aria-label="Abrir análise de risco da carteira"',
                       'data-vestra-go="portfolio"'):
            with self.subTest(marker=marker):
                self.assertIn(marker, home)

    def test_risk_is_a_subordinate_editorial_detail_not_a_competing_card(self):
        css = (ROOT / "vestra-home-first-look-order.css").read_text(encoding="utf-8")
        self.assertIn(".vi-shell>.vi-risk-reading{", css)
        self.assertIn("border-top:1px solid rgba(196,221,208,.22)!important;", css)
        self.assertIn("border-radius:0!important;", css)
        self.assertIn("background:transparent!important;", css)
        self.assertIn("box-shadow:none!important;", css)
        self.assertIn(".vi-shell>.vi-risk-reading::after{", css)
        self.assertIn("content:none!important;", css)
        self.assertIn(".vi-risk-reading-body p{", css)
        self.assertIn("overflow-wrap:anywhere!important;", css)


if __name__ == "__main__":
    unittest.main()
