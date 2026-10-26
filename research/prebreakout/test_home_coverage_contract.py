#!/usr/bin/env python3
"""Static regression: Home pre-breakout coverage must not imply a full-universe rank."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "vestra-intelligence-home.js"

class PrebreakoutCoverageContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_text(encoding="utf-8")

    def test_partial_scope_is_explicit(self):
        self.assertIn("rotating_single_scan_slot_not_full_universe", self.source)
        self.assertIn("ranking parcial", self.source)

    def test_observation_denominator_is_checked(self):
        self.assertIn("audit?.eligible_universe === universe", self.source)
        self.assertIn("observed <= universe", self.source)
        self.assertIn("audit?.window_hours === 24", self.source)

    def test_unknown_coverage_fails_closed(self):
        self.assertIn("Cobertura global não verificada · ranking parcial", self.source)
        self.assertIn("coverageValid", self.source)

    def test_no_predictive_probability_claim(self):
        self.assertIn("Score técnico, não probabilidade", self.source)

if __name__ == "__main__":
    unittest.main()
