"""Guard the Home's evidence-first, non-alarmist portfolio exposure cue."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class NeutralPortfolioExposureTests(unittest.TestCase):
    def test_unverified_concentration_does_not_render_warning_symbol(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        section = re.search(r'<section class="vi-canonical-card vi-risk-reading"[^>]*>(.*?)</section>', html, re.S)
        self.assertIsNotNone(section)
        self.assertIn('<span class="vi-risk-symbol" aria-hidden="true">◇</span>', section.group(1))
        self.assertIn('data-vi-canonical-risk-title', section.group(1))
        self.assertIn('Concentração por verificar', section.group(1))
        self.assertNotIn('>⚠</span>', section.group(1))

    def test_neutral_style_overrides_legacy_amber_and_is_cache_busted(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        css = (ROOT / "vestra-home-first-look-order.css").read_text(encoding="utf-8")
        self.assertIn('vestra-home-first-look-order.css?v=20261101-neutral-risk', html)
        self.assertGreater(html.index('vestra-home-first-look-order.css'), html.index('vestra-intelligence.css'))
        self.assertIn('.vi-shell>.vi-risk-reading .vi-risk-symbol', css)
        self.assertIn('background:rgba(207,228,215,.10)!important', css)
        self.assertIn('.vi-shell>.vi-risk-reading::after', css)


if __name__ == "__main__":
    unittest.main()
