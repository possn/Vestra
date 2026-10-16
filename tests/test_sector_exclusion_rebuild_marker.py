from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class SectorExclusionRebuildTriggerTest(unittest.TestCase):
    def test_explicit_marker_requires_diagnostics_and_canonical_workflow(self):
        marker = (ROOT / ".github/triggers/market-data-rebuild.txt").read_text(encoding="utf-8")
        workflow = (ROOT / ".github/workflows/update-market-data.yml").read_text(encoding="utf-8")
        run = (ROOT / "scripts/run.py").read_text(encoding="utf-8")
        self.assertIn("2026-10-16 — explicit canonical rebuild after #1318", marker)
        self.assertIn("'.github/triggers/market-data-rebuild.txt'", workflow)
        self.assertIn("SECTOR_RELATIVE_EXCLUSIONS", run)

if __name__ == "__main__":
    unittest.main()
