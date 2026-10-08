"""Regression contract for the opt-in Vestra Intelligence visual shell."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class VestraIntelligenceVisualTests(unittest.TestCase):
    def test_css_is_scoped_and_safe_before_rollout(self):
        css = (ROOT / "vestra-intelligence.css").read_text(encoding="utf-8")
        self.assertIn('[data-vestra-intelligence="1"]', css)
        self.assertIn("prefers-reduced-motion", css)
        self.assertIn("safe-area-inset-bottom", css)
        self.assertIn('data-status="missing"', css)
        self.assertIn('data-status="stale"', css)
        # The opt-in layer must not be used by the legacy UI until tested.
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertNotIn('href="vestra-intelligence.css"', html)


if __name__ == "__main__":
    unittest.main()
