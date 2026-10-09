from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class SharedSurfaceTokens(unittest.TestCase):
    def test_palette_and_dossier_usage(self):
        base=(ROOT/"vestra-design-v2.css").read_text()
        shell=(ROOT/"vestra-market-dossier-shell-v2.css").read_text()
        for token in ["--vestra-surface-petrol: #0d2423","--vestra-surface-petrol-ink: #f3eee4","--vestra-surface-ivory: #f0eee7","--vestra-surface-ivory-ink: #173037","--vestra-surface-gold: #e3cd9b"]:
            self.assertIn(token,base)
        for token in ["var(--vestra-surface-petrol)","var(--vestra-surface-petrol-ink)","var(--vestra-surface-gold)"]:
            self.assertIn(token,shell)
    def test_cache_versions(self):
        html=(ROOT/"index.html").read_text()
        self.assertIn("vestra-design-v2.css?v=2",html)
        self.assertIn("vestra-market-dossier-shell-v2.css?v=2",html)
