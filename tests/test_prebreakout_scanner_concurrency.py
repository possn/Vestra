#!/usr/bin/env python3
"""Guard scanner recovery against GitHub Actions self-cancellation."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/refresh-prebreakout-scanner.yml"

class PrebreakoutScannerConcurrencyContract(unittest.TestCase):
    def test_scans_are_serialized_not_cancelled(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        block = source.split("\nconcurrency:\n", 1)[1].split("\njobs:\n", 1)[0]
        self.assertIn("group: refresh-prebreakout-scanner", block)
        self.assertIn("cancel-in-progress: false", block)
        self.assertNotIn("cancel-in-progress: true", block)

    def test_recovery_triggers_cover_early_and_late_slots(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("17,47 2-4,8-10,14-16,20-22 * * 1-5", source)
        self.assertIn("17 5,11,17,23 * * 1-5", source)
        self.assertIn("17,47 2-4,8-10 * * 6", source)
        self.assertIn("17 5,11 * * 6", source)
        self.assertNotIn("10 2,8,14,20 * * 1-5", source)

    def test_slot_deduplication_is_checked_before_scan(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python scripts/check_prebreakout_scan_due.py", source)
        self.assertIn("if: steps.scan_due.outputs.scan == 'true'", source)

if __name__ == "__main__":
    unittest.main()
