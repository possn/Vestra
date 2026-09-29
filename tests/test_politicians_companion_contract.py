from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PoliticiansCompanionContractTests(unittest.TestCase):
    def test_runtime_publishes_loader_marker_once(self):
        source = (ROOT / "politicians.js").read_text(encoding="utf-8")
        self.assertEqual(source.count("window.VestraPoliticians=Object.freeze"), 1)
        self.assertIn("version:VERSION", source)
        self.assertIn("open:openPoliticians", source)

    def test_static_loader_uses_same_companion_marker(self):
        loader = (ROOT / "market-static-universe.js").read_text(encoding="utf-8")
        self.assertIn("VestraPoliticians", loader)


if __name__ == "__main__":
    unittest.main(verbosity=2)
