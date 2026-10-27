#!/usr/bin/env python3
"""Recovery from a separate workflow must retain due and immutable-slot guards."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
RECOVERY=ROOT/".github/workflows/recover-prebreakout-independent.yml"
SCANNER=ROOT/".github/workflows/refresh-prebreakout-scanner.yml"

class IndependentRecoveryContract(unittest.TestCase):
    def test_dispatch_from_unrelated_dashboard_workflow(self):
        s=RECOVERY.read_text(encoding="utf-8")
        self.assertIn('workflows: ["Update dashboard news"]',s)
        self.assertIn("types: [completed]",s)
        self.assertIn("github.event.workflow_run.event == 'schedule'",s)
        self.assertIn("actions: write",s)
        self.assertNotIn("refresh-prebreakout-scanner",s.split("jobs:",1)[0])

    def test_due_check_precedes_canonical_dispatch(self):
        s=RECOVERY.read_text(encoding="utf-8")
        check="python scripts/check_prebreakout_scan_due.py"
        dispatch="gh workflow run refresh-prebreakout-scanner.yml --ref main"
        self.assertIn("ref: main",s)
        self.assertLess(s.index(check),s.index(dispatch))
        self.assertIn("if: steps.scan_due.outputs.scan == 'true'",s)
        self.assertIn("cancel-in-progress: false",s)
        self.assertIn("group: refresh-prebreakout-scanner",SCANNER.read_text(encoding="utf-8"))

if __name__=="__main__":
    unittest.main()
