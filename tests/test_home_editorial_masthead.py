"""Protect the concise Home 2.0 masthead and its live functional hooks."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class HomeEditorialMastheadTests(unittest.TestCase):
    def test_one_clear_edition_without_repeated_labels(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        home = html.split('<section id="vestraIntelligenceHome"', 1)[1].split('</section>\n\n<div class="vi-back-to-intelligence">', 1)[0]
        self.assertIn('INTELLIGENCE / 2.0', home)
        self.assertIn('class="vi-preview-label"', home)
        self.assertIn('LEITURA ATUAL', home)
        self.assertIn('01 / PANORAMA', home)
        self.assertNotIn('VESTRA / EDIÇÃO DO DIA', home)
        self.assertNotIn('EDIÇÃO 02', home)
        self.assertNotIn('INTELLIGENCE / LEITURA ATUAL', home)
        self.assertNotIn('>LEITURA DO DIA</span>', home)

    def test_live_reading_and_navigation_are_preserved(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        home = html.split('<section id="vestraIntelligenceHome"', 1)[1].split('</section>\n\n<div class="vi-back-to-intelligence">', 1)[0]
        for marker in (
            'class="vi-live-dot"', 'data-vi-wealth', 'data-vi-privacy',
            'data-vi-canonical-score', 'data-vi-canonical-news-list',
            'data-vi-canonical-event-list', 'data-vestra-go="portfolio"',
            'class="vi-research-details"',
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, home)


if __name__ == "__main__":
    unittest.main()
