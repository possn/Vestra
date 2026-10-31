"""Home 2.0: portfolio risk is evidence, not an action after the investigations."""
from html.parser import HTMLParser
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class HomeSections(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.seen = []

    def handle_starttag(self, tag, attrs):
        if tag != "section":
            return
        values = dict(attrs)
        classes = set(values.get("class", "").split())
        parents = tuple(self.stack)
        for key in ("vi-home-overview", "vi-canonical-sections",
                    "vi-market-reading", "vi-news-reading", "vi-events-reading",
                    "vi-risk-reading", "vi-priorities"):
            if key in classes:
                self.seen.append((key, parents))
        self.stack.append(classes)

    def handle_endtag(self, tag):
        if tag == "section":
            self.stack.pop()


class HomeRiskEvidenceOrderTests(unittest.TestCase):
    def test_risk_is_last_canonical_evidence_before_investigations(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        home = html.split('<section id="vestraIntelligenceHome"', 1)[1].split(
            '<div class="vi-back-to-intelligence">', 1)[0]
        parsed = HomeSections()
        parsed.feed('<section ' + home)
        keys = [key for key, _ in parsed.seen]
        for key in ("vi-home-overview", "vi-canonical-sections",
                    "vi-market-reading", "vi-news-reading", "vi-events-reading",
                    "vi-risk-reading", "vi-priorities"):
            self.assertEqual(keys.count(key), 1, key)
        self.assertLess(keys.index("vi-home-overview"), keys.index("vi-market-reading"))
        self.assertLess(keys.index("vi-market-reading"), keys.index("vi-news-reading"))
        self.assertLess(keys.index("vi-news-reading"), keys.index("vi-events-reading"))
        self.assertLess(keys.index("vi-events-reading"), keys.index("vi-risk-reading"))
        self.assertLess(keys.index("vi-risk-reading"), keys.index("vi-priorities"))
        parents = dict(parsed.seen)["vi-risk-reading"]
        self.assertTrue(any("vi-canonical-sections" in classes for classes in parents))

    def test_risk_values_and_navigation_remain_live(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        home = html.split('<section id="vestraIntelligenceHome"', 1)[1].split(
            '<div class="vi-back-to-intelligence">', 1)[0]
        for marker in ("data-vi-canonical-risk-title", "data-vi-canonical-risk",
                       "data-vi-canonical-risk-value",
                       'aria-label="Abrir análise de risco da carteira"',
                       'data-vestra-go="portfolio"',
                       'class="vi-decisions"'):
            with self.subTest(marker=marker):
                self.assertIn(marker, home)

    def test_risk_is_fourth_in_visual_flex_order(self):
        css = (ROOT / "vestra-home-first-look-order.css").read_text(encoding="utf-8")
        self.assertIn(".vi-risk-reading{\n order:4!important;", css)
        for section, order in (("market", 1), ("news", 2), ("events", 3)):
            self.assertIn(f".vi-{section}-reading{{\n order:{order}!important;", css)


if __name__ == "__main__":
    unittest.main()
