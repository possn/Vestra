import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class RotationFreshnessContract(unittest.TestCase):
    def test_card_displays_actual_canonical_snapshot_date(self):
        src = (ROOT / "market.js").read_text(encoding="utf-8")
        self.assertIn("M.data?.generated_at", src)
        self.assertIn("weeklyRotationFreshness()", src)
        self.assertIn("${esc(freshness.label)}", src)
        self.assertIn("Leitura histórica", src)
        self.assertIn("ageHours > 30", src)
if __name__ == "__main__":
    unittest.main()
