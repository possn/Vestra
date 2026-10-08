"""Contract: real coverage status, freshness, and fail-closed handling."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class HomeEvidenceTests(unittest.TestCase):
    def test_source_and_fail_closed_rendering(self):
        js=(ROOT/'vestra-intelligence-home.js').read_text()
        html=(ROOT/'index.html').read_text()
        self.assertIn("params.get('vestra2') !== '0'",js)
        self.assertIn("if (!enabled) return;",js)
        self.assertIn("fetch('./data/coverage_guard.json'",js)
        self.assertIn("cache:'no-store'",js)
        self.assertIn("ageHours <= 36",js)
        self.assertIn("guard.ok === true && violations === 0",js)
        self.assertIn("Number.isInteger(rows)",js)
        self.assertIn("data-vestra-coverage",html)
        self.assertIn("Cobertura publicada indisponível",js)
        self.assertNotIn("state.assets",js)
if __name__=='__main__': unittest.main()
