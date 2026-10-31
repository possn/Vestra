"""Guard the actual Home 2.0 reading hierarchy and accessible investigation links."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class HomeEditorialActionsOrderTests(unittest.TestCase):
    def test_conclusion_evidence_actions_then_detail(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        anchors = (
            '<section class="vi-home-overview"',
            '<section class="vi-context-chapter"',
            '<section class="vi-priorities"',
            '<section class="vi-canonical-card vi-risk-reading"',
            '<details class="vi-research-details"',
        )
        positions = [html.index(anchor) for anchor in anchors]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("Primeiro a leitura e a evidência. Depois, as decisões.", html)
        self.assertEqual(html.count('class="vi-card vi-action"'), 3)

    def test_actions_style_targets_real_dom_and_preserves_accessibility(self):
        css = (ROOT / "vestra-home-first-look-order.css").read_text(encoding="utf-8")
        chapter = css.split("Canonical Home DOM: overview -> market evidence", 1)[1]
        self.assertIn(".vi-shell>.vi-priorities", chapter)
        self.assertIn("grid-template-columns:repeat(3,minmax(0,1fr))", chapter)
        self.assertIn("grid-template-columns:minmax(0,1fr)", chapter)
        self.assertIn(".vi-action:focus-visible", chapter)
        self.assertIn("outline:2px solid", chapter)
        self.assertNotIn("display:none", chapter)
        self.assertNotIn("visibility:hidden", chapter)


if __name__ == "__main__":
    unittest.main()
