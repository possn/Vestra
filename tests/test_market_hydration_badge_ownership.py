from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
LOADER = ROOT / "market-data-loader.js"


class MarketHydrationBadgeOwnershipTests(unittest.TestCase):
    def test_loading_generation_invalidates_older_removal_timeout(self):
        text = LOADER.read_text(encoding="utf-8")
        self.assertIn("badge.dataset.hydrationGeneration=String((Number(badge.dataset.hydrationGeneration)||0)+1)", text)
        self.assertIn("const generation=badge.dataset.hydrationGeneration||''", text)
        self.assertIn("badge.dataset.hydrationGeneration===generation", text)
        self.assertIn("badge.textContent===label", text)
        self.assertNotIn("if(badge?.isConnected) badge.remove()", text)

    def test_ready_and_partial_keep_existing_display_delays(self):
        text = LOADER.read_text(encoding="utf-8")
        self.assertIn("const label=state==='ready'?'✓ Dossier completo':'Detalhe parcial'", text)
        self.assertIn("const delay=state==='ready'?1400:1800", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
