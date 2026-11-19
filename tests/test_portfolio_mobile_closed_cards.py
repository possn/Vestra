"""Mobile portfolio closed-card readability contract."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PortfolioMobileClosedCardTests(unittest.TestCase):
    def test_closed_cards_keep_readable_titles_and_clear_action_space(self):
        css = (ROOT / "vestra-portfolio-ui.css").read_text(encoding="utf-8")
        self.assertIn(".vpu-section-card.is-collapsed", css)
        self.assertIn("padding:15px 62px 15px 16px!important", css)
        self.assertIn("font-size:17px!important", css)
        self.assertIn("word-break:normal!important", css)
        self.assertIn(".market-target-fit-score", css)

    def test_mobile_styles_are_not_delayed_by_the_pwa(self):
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        worker = (ROOT / "sw.js").read_text(encoding="utf-8")
        self.assertIn('vestra-portfolio-ui.css?v=3.5-guided', index)
        self.assertIn('vestra-cache-v276', worker)


if __name__ == "__main__":
    unittest.main()
